"""Regex-based PII detection/masking. Runs on every payload before it reaches
a prompt, regardless of which LLM provider is active — masking happens
upstream of the client so cached fixtures are also safe to inspect/ship.
Deliberately simple (no Presidio/spaCy) to keep the dependency tree small for
a locked-down laptop; swap for Presidio if this ever moves toward production.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "ACCOUNT_NUMBER": re.compile(r"\b\d{8,12}\b"),
    "SIN_OR_SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{3}\s\d{3}\s\d{3}\b"),
    "PHONE": re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
}


@dataclass
class MaskingResult:
    masked_text: str
    token_map: dict[str, str] = field(default_factory=dict)  # token -> original


def mask(text: str) -> MaskingResult:
    token_map: dict[str, str] = {}
    counters: dict[str, int] = {}

    def replace(label: str, value: str) -> str:
        counters[label] = counters.get(label, 0) + 1
        token = f"[{label}_{counters[label]}]"
        token_map[token] = value
        return token

    masked = text
    for label, pattern in _PATTERNS.items():
        masked = pattern.sub(lambda m, label=label: replace(label, m.group(0)), masked)
    return MaskingResult(masked_text=masked, token_map=token_map)


def unmask(text: str, token_map: dict[str, str]) -> str:
    """Re-hydrate tokens for display — call only after an RBAC check confirms
    the requesting user is authorized to see the underlying values.
    """
    result = text
    for token, original in token_map.items():
        result = result.replace(token, original)
    return result
