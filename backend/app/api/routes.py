"""The critical route: run a case through the guarded GenAI investigation
pipeline. Guardrail order matters — PII is masked before anything reaches the
LLM client (so it's masked regardless of which provider is active), citations
are validated deterministically after generation, and nothing here ever
auto-executes an action — 'approve' is a separate, explicit human step.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.agents.chat import ask_precedent_question
from app.agents.pipeline import investigate_case
from app.agents.suggested_questions import get_suggested_questions, resolve_question_text
from app.cases import build_case_context, get_case_detail, list_alerts, list_cases
from app.llm.client import get_llm_client
from app.security import audit
from app.security.pii import mask
from app import knowledge

logger = logging.getLogger(__name__)

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


class ChatRequest(BaseModel):
    question: str = ""
    question_id: str | None = None


@router.get("/cases")
async def get_cases(x_demo_role: str | None = Header(default=None)):
    _require_role(x_demo_role)
    return {"cases": list_cases()}


@router.get("/alerts")
async def get_alerts(x_demo_role: str | None = Header(default=None)):
    _require_role(x_demo_role)
    return {"alerts": list_alerts()}


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

    try:
        key_claims = [c["statement"] for c in result.prosecutor.get("claims", []) + result.defense.get("claims", [])]
        knowledge.record_investigation(
            case_id=case_id,
            typology=get_case_detail(case_id)["typology_guess"],
            verdict=result.verdict["verdict"],
            confidence=result.verdict["confidence"],
            flagged_for_review=result.flagged_for_review,
            narrative=result.verdict["narrative"],
            key_claims=key_claims,
            citations=result.verdict.get("citations", []),
            actor=actor,
        )
    except Exception:
        # The knowledge base is a secondary search index, not the
        # compliance-critical path — a failure here must never break the
        # actual investigation response the investigator is waiting on.
        logger.warning("Failed to record knowledge entry for %s", case_id, exc_info=True)

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

    try:
        detail = get_case_detail(case_id)
        knowledge.record_decision(
            case_id=case_id,
            typology=detail["typology_guess"] if detail else "unknown",
            decision=body.decision,
            narrative=body.note,
            actor=actor,
        )
    except Exception:
        logger.warning("Failed to record knowledge decision entry for %s", case_id, exc_info=True)

    return {"status": "recorded"}


@router.get("/cases/{case_id}/audit")
async def get_audit_trail(case_id: str, x_demo_role: str | None = Header(default=None)):
    _require_role(x_demo_role)
    return {"case_id": case_id, "trail": audit.get_trail(case_id)}


@router.get("/cases/{case_id}/chat/suggested-questions")
async def get_chat_suggestions(case_id: str, x_demo_role: str | None = Header(default=None)):
    _require_role(x_demo_role)
    detail = get_case_detail(case_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found.")
    return {"questions": get_suggested_questions(detail["typology_guess"])}


@router.post("/cases/{case_id}/chat")
async def chat(case_id: str, body: ChatRequest, x_demo_role: str | None = Header(default=None)):
    # Read-only reference tool available to every role — not an approval
    # action, so no extra role gate beyond the standard one.
    _require_role(x_demo_role)

    detail = get_case_detail(case_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found.")

    question = body.question.strip()
    if body.question_id:
        resolved = resolve_question_text(detail["typology_guess"], body.question_id)
        if resolved is None:
            raise HTTPException(status_code=400, detail=f"Unknown question_id {body.question_id!r} for this case's typology.")
        question = resolved
    if not question:
        raise HTTPException(status_code=400, detail="question or a valid question_id is required.")

    llm = get_llm_client()
    try:
        result = await ask_precedent_question(llm, case_id=case_id, question=question, question_id=body.question_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "case_id": case_id,
        "question": question,
        "answer": result.answer,
        "citations": result.citations,
        "confidence": result.confidence,
        "source": result.source,
        "unverified_case_ids": result.unverified_case_ids,
        "precedent_case_ids_considered": result.precedent_case_ids_considered,
    }
