"""Precedent knowledge base — the "feedback loop" that builds up as
investigators work cases, and the corpus backing agents/chat.py's "have we
seen something like this before" retrieval.

Deliberately a separate, un-hash-chained table from app/security/audit.py's
audit_log, not an extension of it. audit_log is the compliance-critical,
tamper-evident record of what happened and who signed off — that's exactly
what a hash chain is for. knowledge_entries is a derived search index built
from the same events to make investigators faster; it's disposable and
re-derivable from audit_log + cases at any time, so hash-chaining it would
add real complexity (chain maintenance, no ability to ever curate an entry)
for zero compliance benefit. Never wiped by app.db.reset_case_data(), same
as audit_log — the case_id it references stays stable across dataset
regenerations because data/generate_dataset.py uses a fixed random seed.

Retrieval is local TF-IDF cosine similarity (numpy, already a dependency,
otherwise unused) plus a same-typology boost — not a third-party embeddings
API. For a corpus of a dozen-ish cases, an embeddings API would be a new
credential and a new offline-availability risk stacked on the LLM-access
risk this project is already built around avoiding, for a quality gain that
wouldn't be visible in a demo. Retrieval itself never touches an LLM, so it
never needs a cache fixture and never breaks offline — only the final
answer-composition call in agents/chat.py does.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

DB_PATH = Path(__file__).resolve().parents[1] / "investigenius.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    typology TEXT NOT NULL,
    event_type TEXT NOT NULL,
    verdict TEXT,
    decision TEXT,
    confidence REAL,
    flagged_for_review INTEGER,
    narrative TEXT NOT NULL DEFAULT '',
    key_claims TEXT NOT NULL DEFAULT '[]',
    citations TEXT NOT NULL DEFAULT '[]',
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_knowledge_case_id ON knowledge_entries(case_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_typology ON knowledge_entries(typology);
"""

# Generic terms that appear in nearly every case narrative regardless of what
# actually distinguishes it — filtered so IDF weighting isn't drowned out by
# words like "account" and "transaction" that carry no discriminative signal
# in this domain. Combined with a small standard English stopword list.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "was",
    "were", "be", "this", "that", "with", "as", "by", "at", "from", "it",
    "its", "into", "within", "each", "which", "has", "have", "had", "not",
    "no", "than", "then", "there", "their", "them", "these", "those", "any",
    "account", "accounts", "transaction", "transactions", "transfer",
    "transfers", "case", "cases", "client", "clients",
}
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 2]


def record_investigation(
    *, case_id: str, typology: str, verdict: str, confidence: float,
    flagged_for_review: bool, narrative: str, key_claims: list[str], citations: list[str], actor: str,
) -> None:
    import json

    conn = connect()
    try:
        conn.execute(
            """INSERT INTO knowledge_entries
               (case_id, typology, event_type, verdict, confidence, flagged_for_review, narrative, key_claims, citations, actor)
               VALUES (?, ?, 'investigation', ?, ?, ?, ?, ?, ?, ?)""",
            (case_id, typology, verdict, confidence, int(flagged_for_review), narrative,
             json.dumps(key_claims), json.dumps(citations), actor),
        )
        conn.commit()
    finally:
        conn.close()


def record_decision(*, case_id: str, typology: str, decision: str, narrative: str, actor: str) -> None:
    conn = connect()
    try:
        conn.execute(
            """INSERT INTO knowledge_entries (case_id, typology, event_type, decision, narrative, actor)
               VALUES (?, ?, 'decision', ?, ?, ?)""",
            (case_id, typology, decision, narrative, actor),
        )
        conn.commit()
    finally:
        conn.close()


def _load_corpus(exclude_case_id: str | None) -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute("SELECT * FROM knowledge_entries ORDER BY case_id, id ASC").fetchall()
    finally:
        conn.close()

    by_case: dict[str, dict[str, Any]] = {}
    for r in rows:
        if exclude_case_id and r["case_id"] == exclude_case_id:
            continue
        entry = by_case.setdefault(r["case_id"], {
            "case_id": r["case_id"], "typology": r["typology"], "text_parts": [],
            "verdict": None, "decision": None, "best_narrative": "",
        })
        entry["text_parts"].append(r["narrative"])
        if r["event_type"] == "investigation":
            entry["verdict"] = r["verdict"]
            if not entry["best_narrative"]:
                entry["best_narrative"] = r["narrative"]
        elif r["event_type"] == "decision":
            entry["decision"] = r["decision"]
            entry["best_narrative"] = r["narrative"] or entry["best_narrative"]
    return list(by_case.values())


def search_precedents(*, query_text: str, typology: str, exclude_case_id: str | None, top_n: int = 3) -> list[dict[str, Any]]:
    """Local TF-IDF cosine similarity + a same-typology boost. Returns [] if
    the knowledge base is empty (or has nothing but the current case) rather
    than erroring — an empty result is a legitimate, expected state early on,
    and agents/chat.py is responsible for saying so honestly rather than
    inventing a precedent that doesn't exist.
    """
    corpus = _load_corpus(exclude_case_id)
    if not corpus:
        return []

    docs = [_tokenize(" ".join(c["text_parts"])) for c in corpus]
    query_tokens = _tokenize(query_text)

    vocab = sorted({t for doc in docs for t in doc})
    if not vocab or not query_tokens:
        scores = [0.3 if c["typology"] == typology else 0.0 for c in corpus]
    else:
        idx = {t: i for i, t in enumerate(vocab)}
        n_docs = len(docs)

        doc_freq = np.zeros(len(vocab))
        for doc in docs:
            for t in set(doc):
                doc_freq[idx[t]] += 1
        idf = np.log((n_docs + 1) / (doc_freq + 1)) + 1

        def tfidf_vector(tokens: list[str]) -> np.ndarray:
            vec = np.zeros(len(vocab))
            for t in tokens:
                if t in idx:
                    vec[idx[t]] += 1
            if tokens:
                vec = vec / len(tokens)
            vec = vec * idf
            norm = np.linalg.norm(vec)
            return vec / norm if norm > 0 else vec

        doc_matrix = np.array([tfidf_vector(doc) for doc in docs])
        query_vec = tfidf_vector(query_tokens)
        scores = doc_matrix @ query_vec

        scores = [s + (0.3 if c["typology"] == typology else 0.0) for s, c in zip(scores, corpus)]

    ranked = sorted(zip(scores, corpus), key=lambda pair: pair[0], reverse=True)
    results = []
    for score, c in ranked[:top_n]:
        if score <= 0:
            continue
        results.append({
            "case_id": c["case_id"],
            "typology": c["typology"],
            "verdict": c["verdict"],
            "decision": c["decision"],
            "narrative": c["best_narrative"],
            "score": round(float(score), 3),
        })
    return results
