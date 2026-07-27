"""Records real LLM fixtures for the precedent-chat feature's suggested
questions, by driving app.agents.chat.ask_precedent_question against the
live Anthropic API for each (case_id, question_id) pair. Same philosophy as
record_fixtures.py: this drives the real code path, AnthropicClient
auto-saves the fixture as a side effect — not a separate mock generator.

Ordering matters. Chat retrieval needs a populated knowledge base to have
anything real to cite, so run this AFTER:
  1. record_fixtures.py has recorded investigations for the demo cases
     (which now also populates knowledge_entries as a side effect).
  2. You've clicked Approve/Reject on a few of those cases in the running
     app, varied typologies, at least one reject — real audit_log +
     knowledge_entries data. Doing this by hand in the UI is exactly
     equivalent to a seeding script but needs zero extra code.
Recording chat fixtures against an empty/thin knowledge base just bakes in
weak "no relevant precedent found" answers.

Requires (in backend/.env):
  LLM_PROVIDER=anthropic
  ANTHROPIC_API_KEY=<your key>
Switch LLM_PROVIDER back to 'cache' before zipping for the bank laptop —
same as record_fixtures.py, this script does not do that for you.

Usage (from repo root):
  backend/.venv/Scripts/python.exe scripts/record_chat_fixtures.py
  backend/.venv/Scripts/python.exe scripts/record_chat_fixtures.py case_001 case_005
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

from app.agents.chat import ask_precedent_question  # noqa: E402
from app.agents.suggested_questions import get_suggested_questions  # noqa: E402
from app.cases import get_case_detail  # noqa: E402
from app.llm.client import get_llm_client  # noqa: E402

DEFAULT_CASE_IDS = ["case_001", "case_005", "case_007", "case_013"]


async def record_for_case(case_id: str, failed: list[str]) -> None:
    detail = get_case_detail(case_id)
    if detail is None:
        print(f"  {case_id}: not found in the database, skipping")
        return

    questions = get_suggested_questions(detail["typology_guess"])
    llm = get_llm_client()
    for q in questions:
        try:
            result = await ask_precedent_question(llm, case_id=case_id, question=q["text"], question_id=q["question_id"])
            n_precedents = len(result.precedent_case_ids_considered) if result else 0
            print(f"  {case_id} / {q['question_id']}: {n_precedents} precedent(s) considered")
        except RuntimeError as exc:
            # Same validated-response guarantee as record_fixtures.py — a bad
            # response on one question shouldn't abort the whole batch.
            print(f"  {case_id} / {q['question_id']}: FAILED — {exc}")
            failed.append(f"{case_id}/{q['question_id']}")


async def main(case_ids: list[str]) -> None:
    if os.environ.get("LLM_PROVIDER") != "anthropic":
        raise SystemExit(
            "LLM_PROVIDER is not set to 'anthropic' in backend/.env — refusing to run, "
            "since this would silently hit the cache client instead of the real API."
        )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set in backend/.env.")

    print(f"Recording chat fixtures for {len(case_ids)} case(s) via LIVE Anthropic API calls:")
    failed: list[str] = []
    for case_id in case_ids:
        await record_for_case(case_id, failed)
    print(
        "\nDone. Fixtures written to backend/cache/fixtures/. "
        "Set LLM_PROVIDER back to 'cache' in backend/.env before zipping for the bank laptop."
    )
    if failed:
        print(f"\n{len(failed)} question(s) failed and were skipped: {failed}. Re-run this script (it'll redo everything) or wait and retry — these are stochastic generation issues, not deterministic bugs.")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or DEFAULT_CASE_IDS))
