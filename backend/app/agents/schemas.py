"""JSON schemas for structured LLM output. Every agent call is constrained to
one of these — no free-text parsing anywhere in the pipeline.
"""

ARGUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
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
    },
    "required": ["summary", "claims"],
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["escalate", "close", "needs_review"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "narrative": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "confidence", "narrative", "citations"],
}
