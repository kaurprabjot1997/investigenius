"""Shared SQLite schema for case data. Separate from app/security/audit.py's
own connection to the same file — SQLite handles concurrent module-level
`CREATE TABLE IF NOT EXISTS` calls fine, and keeping audit writes isolated
from case data means a bug in one schema can't corrupt the other's table.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "investigenius.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    account_type TEXT NOT NULL,
    kyc_notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id TEXT PRIMARY KEY,
    from_account TEXT NOT NULL,
    to_account TEXT NOT NULL,
    amount REAL NOT NULL,
    ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    txn_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    raised_at TEXT NOT NULL
);

-- Mock client-profile enrichment, field categories inspired by RBC's UCP4.0
-- data dictionary (demographics, tenure, income/credit bands, digital
-- engagement, product holdings, segmentation) — see data/profiles.py for the
-- generator and the governance note on why segmentation fields are shown to
-- investigators but deliberately excluded from the automated risk score.
CREATE TABLE IF NOT EXISTS client_profiles (
    account_id TEXT PRIMARY KEY,
    age_range TEXT NOT NULL DEFAULT '',
    generation TEXT NOT NULL DEFAULT '',
    tenure_years REAL NOT NULL DEFAULT 0,
    income_after_tax_range TEXT NOT NULL DEFAULT '',
    credit_score_range TEXT NOT NULL DEFAULT '',
    occupation TEXT NOT NULL DEFAULT '',
    residence_country TEXT NOT NULL DEFAULT '',
    non_resident_tax_flag INTEGER NOT NULL DEFAULT 0,
    new_to_canada_segment INTEGER NOT NULL DEFAULT 0,
    digital_enrolled INTEGER NOT NULL DEFAULT 0,
    digital_active_ind INTEGER NOT NULL DEFAULT 0,
    mobile_auth_ind INTEGER NOT NULL DEFAULT 0,
    active_product_count INTEGER NOT NULL DEFAULT 0,
    total_relationship_balance REAL NOT NULL DEFAULT 0,
    profitability_segment TEXT NOT NULL DEFAULT '',
    vulnerability_segment TEXT NOT NULL DEFAULT '',
    wallet_band_segment TEXT NOT NULL DEFAULT '',
    client_product_segment TEXT NOT NULL DEFAULT '',
    staff_flag INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    typology_guess TEXT NOT NULL,
    risk_score REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS case_accounts (
    case_id TEXT NOT NULL,
    account_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_alerts (
    case_id TEXT NOT NULL,
    alert_id TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def reset_case_data(conn: sqlite3.Connection) -> None:
    """Wipes generated/derived data only — never touches audit_log, so
    regenerating the demo dataset never erases the audit trail's history.
    """
    for table in ["case_alerts", "case_accounts", "cases", "alerts", "transactions", "client_profiles", "accounts"]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


def executemany(conn: sqlite3.Connection, sql: str, rows: list[tuple[Any, ...]]) -> None:
    conn.executemany(sql, rows)
    conn.commit()
