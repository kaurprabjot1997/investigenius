"""JSON schemas for structured LLM output. Every agent call is constrained to
one of these — no free-text parsing anywhere in the pipeline.

Structured fields are listed before the long free-text field in every schema
below (claims/citations before summary/narrative/answer) — not just for
readability. In practice, forced tool-use occasionally drops the field that
comes *after* a long free-text field entirely (seen repeatedly during fixture
recording: 'citations' or 'claims' missing while the narrative/summary/answer
text came through fine, always the trailing field, never the leading one).
Putting the short structured fields first means the model commits to them
before it has spent its effort on the verbose prose, which is a known
mitigation for this failure mode. app/llm/client.py's AnthropicClient still
validates all required fields are present and retries regardless — this is
a defense-in-depth reliability improvement, not a replacement for that check.
"""

ARGUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "citation_id": {
                        "type": "string",
                        "description": "Record ID (transaction/entity) from the case context that supports this claim.",
                    },
                    "typology": {"type": "string"},
                },
                "required": ["statement", "citation_id"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["claims", "summary"],
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["escalate", "close", "needs_review"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "citations": {"type": "array", "items": {"type": "string"}},
        "narrative": {"type": "string"},
    },
    "required": ["verdict", "confidence", "citations", "narrative"],
}

CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "A prior case_id from the retrieved precedents that supports this part of the answer."},
                    "note": {"type": "string", "description": "What about that precedent is relevant."},
                },
                "required": ["case_id", "note"],
            },
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "answer": {"type": "string"},
    },
    "required": ["citations", "confidence", "answer"],
}
