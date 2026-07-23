"""The critical route: run a case through the guarded GenAI investigation
pipeline. Guardrail order matters — PII is masked before anything reaches the
LLM client (so it's masked regardless of which provider is active), citations
are validated deterministically after generation, and nothing here ever
auto-executes an action — 'approve' is a separate, explicit human step.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.agents.pipeline import investigate_case
from app.cases import build_case_context, get_case_detail, list_cases
from app.llm.client import get_llm_client
from app.security import audit
from app.security.pii import mask

router = APIRouter()

_VALID_ROLES = {"junior_investigator", "senior_investigator", "compliance_officer"}


def _require_role(x_demo_role: str | None) -> str:
    # Stand-in for real auth (Section 2 simplification: role switcher, not a
    # hardened auth system) — still enforced server-side, not just hidden in
    # the UI, so the RBAC *shape* of the design is real even if the auth
    # mechanism backing it is intentionally minimal for the demo.
    if x_demo_role not in _VALID_ROLES:
        raise HTTPException(status_code=403, detail=f"Unknown or missing role: {x_demo_role!r}")
    return x_demo_role


class InvestigateResponse(BaseModel):
    case_id: str
    prosecutor: dict
    defense: dict
    verdict: dict
    flagged_for_review: bool
    uncited_claims: list[str]
    source: str  # "live" | "cache" — never hidden from the reviewer


class ApproveRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    note: str = ""


@router.get("/cases")
async def get_cases(x_demo_role: str | None = Header(default=None)):
    _require_role(x_demo_role)
    return {"cases": list_cases()}


@router.get("/cases/{case_id}")
async def get_case(case_id: str, x_demo_role: str | None = Header(default=None)):
    _require_role(x_demo_role)
    detail = get_case_detail(case_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found.")
    return detail


@router.post("/cases/{case_id}/investigate", response_model=InvestigateResponse)
async def investigate(case_id: str, x_demo_role: str | None = Header(default=None)):
    actor = _require_role(x_demo_role)

    context = build_case_context(case_id)
    if context is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found.")
    case_narrative_raw, record_ids = context

    masked = mask(case_narrative_raw)
    llm = get_llm_client()

    try:
        result = await investigate_case(
            llm,
            case_id=case_id,
            case_context=masked.masked_text,
            known_record_ids=set(record_ids),
        )
    except RuntimeError as exc:
        # Most likely CachedReplayClient hitting an unrecorded case — a 503,
        # not a 500, because it's an environment/config gap, not a bug.
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    audit.record(
        case_id=case_id,
        action="investigate",
        actor=actor,
        payload={
            "verdict": result.verdict["verdict"],
            "confidence": result.verdict["confidence"],
            "flagged_for_review": result.flagged_for_review,
            "uncited_claim_count": len(result.uncited_claims),
        },
    )

    return InvestigateResponse(
        case_id=case_id,
        prosecutor=result.prosecutor,
        defense=result.defense,
        verdict=result.verdict,
        flagged_for_review=result.flagged_for_review,
        uncited_claims=result.uncited_claims,
        source=result.source,
    )


@router.post("/cases/{case_id}/approve")
async def approve(case_id: str, body: ApproveRequest, x_demo_role: str | None = Header(default=None)):
    actor = _require_role(x_demo_role)
    if actor not in {"senior_investigator", "compliance_officer"}:
        raise HTTPException(status_code=403, detail="Only senior investigators or compliance officers may approve.")

    audit.record(
        case_id=case_id,
        action=f"human_{body.decision}",
        actor=actor,
        payload={"note": body.note},
    )
    return {"status": "recorded"}


@router.get("/cases/{case_id}/audit")
async def get_audit_trail(case_id: str, x_demo_role: str | None = Header(default=None)):
    _require_role(x_demo_role)
    return {"case_id": case_id, "trail": audit.get_trail(case_id)}
