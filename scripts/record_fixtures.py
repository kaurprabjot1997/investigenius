"""Records real LLM fixtures for a set of demo cases by driving the actual
investigation pipeline against the live Anthropic API. Every fixture is
written automatically by AnthropicClient.generate_structured as a side
effect of the pipeline running — this script just triggers that, case by
case, so it's the same code path a live request would take, not a separate
mock-generation script.

Requires (in backend/.env):
  LLM_PROVIDER=anthropic
  ANTHROPIC_API_KEY=<your key>
Run this only on a machine with real API access. Switch LLM_PROVIDER back to
'cache' in .env before zipping for the bank laptop — this script does not do
that for you.

Usage (from repo root):
  backend/.venv/Scripts/python.exe scripts/record_fixtures.py case_005 case_007 case_013
  backend/.venv/Scripts/python.exe scripts/record_fixtures.py            # defaults to the 4 featured cases
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND / ".env")

from app.agents.pipeline import investigate_case  # noqa: E402
from app.cases import build_case_context, get_case_detail  # noqa: E402
from app.llm.client import get_llm_client  # noqa: E402
from app.security.pii import mask  # noqa: E402
from app import knowledge  # noqa: E402

DEFAULT_CASE_IDS = ["case_001", "case_005", "case_007", "case_013"]


async def record_one(case_id: str) -> None:
    context = build_case_context(case_id)
    if context is None:
        print(f"  {case_id}: not found in the database, skipping")
        return
    case_narrative_raw, record_ids = context
    masked = mask(case_narrative_raw)
    llm = get_llm_client()
    result = await investigate_case(
        llm, case_id=case_id, case_context=masked.masked_text, known_record_ids=set(record_ids)
    )
    print(
        f"  {case_id}: verdict={result.verdict['verdict']} "
        f"confidence={result.verdict['confidence']:.2f} flagged_for_review={result.flagged_for_review}"
    )

    # Bypasses the HTTP layer, so it needs its own copy of the same
    # knowledge-recording call app/api/routes.py's investigate() makes —
    # otherwise fixtures get recorded but the precedent-chat knowledge base
    # stays empty for these cases.
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
        actor="fixture-recording-script",
    )


async def main(case_ids: list[str]) -> None:
    if os.environ.get("LLM_PROVIDER") != "anthropic":
        raise SystemExit(
            "LLM_PROVIDER is not set to 'anthropic' in backend/.env — refusing to run, "
            "since this would silently hit the cache client instead of the real API."
        )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set in backend/.env.")

    print(f"Recording fixtures for {len(case_ids)} case(s) via LIVE Anthropic API calls:")
    failed = []
    for case_id in case_ids:
        try:
            await record_one(case_id)
        except RuntimeError as exc:
            # A bad response on one case (see app/llm/client.py's validation)
            # shouldn't abort the whole batch — record what succeeds, report
            # what didn't, so a retry only needs to target the failures.
            print(f"  {case_id}: FAILED — {exc}")
            failed.append(case_id)
    print(
        "\nDone. Fixtures written to backend/cache/fixtures/. "
        "Set LLM_PROVIDER back to 'cache' in backend/.env before zipping for the bank laptop."
    )
    if failed:
        print(f"\n{len(failed)} case(s) failed and were skipped: {failed}. Re-run this script with just those case IDs to retry.")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or DEFAULT_CASE_IDS))
