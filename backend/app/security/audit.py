"""Hash-chained audit log. Each row embeds the hash of the previous row's
content, so any retroactive edit to a past entry breaks the chain from that
point forward — a cheap, verifiable tamper-evidence property for a compliance
audience, without needing real blockchain infra.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).resolve().parents[2] / "investigenius.db"
_GENESIS_HASH = "0" * 64


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            payload TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
            prev_hash TEXT NOT NULL,
            row_hash TEXT NOT NULL
        )
        """
    )
    return conn


def _row_hash(prev_hash: str, case_id: str, action: str, actor: str, payload: str, timestamp: str) -> str:
    digest_input = "|".join([prev_hash, case_id, action, actor, payload, timestamp])
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()


def record(*, case_id: str, action: str, actor: str, payload: dict[str, Any]) -> None:
    conn = _connect()
    try:
        cur = conn.execute("SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        prev_hash = row[0] if row else _GENESIS_HASH

        payload_json = json.dumps(payload, sort_keys=True)
        cur = conn.execute(
            "SELECT STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')"
        )
        timestamp = cur.fetchone()[0]
        row_hash = _row_hash(prev_hash, case_id, action, actor, payload_json, timestamp)

        conn.execute(
            """
            INSERT INTO audit_log (case_id, action, actor, payload, timestamp, prev_hash, row_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (case_id, action, actor, payload_json, timestamp, prev_hash, row_hash),
        )
        conn.commit()
    finally:
        conn.close()


def verify_chain_integrity() -> bool:
    """Recomputes every row's hash and checks it against the stored value and
    the next row's prev_hash — a live demo talking point ("run this and prove
    nothing's been tampered with"), not just a design claim.
    """
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT case_id, action, actor, payload, timestamp, prev_hash, row_hash "
            "FROM audit_log ORDER BY id ASC"
        ).fetchall()
    finally:
        conn.close()

    expected_prev = _GENESIS_HASH
    for case_id, action, actor, payload, timestamp, prev_hash, row_hash in rows:
        if prev_hash != expected_prev:
            return False
        if _row_hash(prev_hash, case_id, action, actor, payload, timestamp) != row_hash:
            return False
        expected_prev = row_hash
    return True


def get_trail(case_id: str) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT action, actor, payload, timestamp, row_hash FROM audit_log "
            "WHERE case_id = ? ORDER BY id ASC",
            (case_id,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "action": action,
            "actor": actor,
            "payload": json.loads(payload),
            "timestamp": timestamp,
            "row_hash": row_hash,
        }
        for action, actor, payload, timestamp, row_hash in rows
    ]
