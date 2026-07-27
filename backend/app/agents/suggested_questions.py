"""Curated questions per typology — the single source of truth for both the
suggested-question chips in the UI and the cache-key namespace fixtures get
recorded under (scripts/record_chat_fixtures.py). Free-text questions are
still supported (see app/agents/chat.py), but these are the ones guaranteed
to have a recorded fixture for offline demo mode.
"""
from __future__ import annotations

from typing import Literal

Typology = Literal["structuring", "round_tripping", "mule_hub", "none"]

_GENERIC = [
    {"question_id": "seen_before", "text": "Have we seen a case like this before?"},
    {"question_id": "typical_outcome", "text": "What's the typical outcome for cases like this?"},
]

_BY_TYPOLOGY: dict[Typology, list[dict[str, str]]] = {
    "structuring": [
        {"question_id": "structuring_threshold", "text": "How have similar near-threshold structuring patterns been resolved before?"},
    ],
    "round_tripping": [
        {"question_id": "round_tripping_cycle", "text": "Have similar circular fund-flow cases been escalated or closed?"},
    ],
    "mule_hub": [
        {"question_id": "mule_hub_precedent", "text": "What did we conclude in past cases with a similar high-fan-out hub account?"},
    ],
    "none": [],
}


def get_suggested_questions(typology: Typology) -> list[dict[str, str]]:
    return _GENERIC + _BY_TYPOLOGY.get(typology, [])


def resolve_question_text(typology: Typology, question_id: str) -> str | None:
    for q in get_suggested_questions(typology):
        if q["question_id"] == question_id:
            return q["text"]
    return None
