"""Generates a synthetic AML dataset with deliberately planted typologies
(structuring, round-tripping, mule hub) plus benign noise, and seeds the DB.
Fixed seed so the dataset is reproducible across runs and across laptops —
the same zip always produces the same demo data.

The first structuring scheme uses hardcoded IDs (ACCT-1001..1012, ACCT-9000,
TXN-0001..0013) matching backend/cache/fixtures/case_001_*.json, so the
pre-recorded LLM fixtures stay usable against freshly generated data.

Run from backend/: `py -3.12 -m data.generate_dataset`
"""
from __future__ import annotations

import itertools
import random
from datetime import datetime, timedelta

from app.db import connect, executemany, reset_case_data
from data.profiles import INSERT_SQL as PROFILE_INSERT_SQL
from data.profiles import make_profile

random.seed(42)

# Independent generator, seeded separately, used only for picking alert
# reason text. Deliberately NOT drawing from the shared `random` module used
# everywhere else in this file (amounts, timestamps, tenure bias) — that
# module's call sequence is what makes every non-case_001 case's generated
# data deterministic and reproducible, including the case_005/007/013
# fixtures already recorded against it (real API credits were spent on
# those). Interleaving new random.choice() calls into that shared sequence
# would shift every uniform() draw after them, silently changing transaction
# amounts/timestamps/profiles and invalidating those fixtures. A second,
# separately-seeded Random instance adds reason variety with zero effect on
# the rest of the sequence.
_reason_rng = random.Random(1337)

BASE_DATE = datetime(2026, 7, 10, 9, 0)

# Reason-text variety for the alerts queue — a real AML monitoring system
# fires many differently-worded rules even for the same underlying typology,
# and case_001's exact reason strings are left untouched (make_fixture_
# matched_structuring_scheme below) since they're baked into the already-
# recorded LLM fixture narratives.
STRUCTURING_FEEDER_REASONS = [
    "Sub-$10,000 transfer near CTR threshold",
    "Transaction structured to avoid reporting threshold",
    "Multiple sub-threshold deposits detected",
    "Deposit pattern consistent with structuring",
]
STRUCTURING_CASHOUT_REASONS = [
    "Large same-day consolidated outflow",
    "Rapid fund consolidation and external transfer",
    "Same-day full-balance sweep to external account",
]
ROUND_TRIPPING_REASONS = [
    "Circular fund flow detected",
    "Potential layering — funds returned toward origin",
    "Unusual round-trip transaction pattern",
    "Sequential transfer loop flagged by network monitoring",
]
MULE_HUB_REASONS = [
    "High-frequency third-party transfers",
    "Unusual counterparty velocity",
    "Potential money mule activity — high fan-out",
    "Rapid pass-through transaction pattern",
    "Account transacting with unusually broad counterparty network",
]
BENIGN_REASONS = [
    "Routine monitoring — elevated single transfer",
    "Transaction above dynamic account threshold",
    "New payee — first-time transfer",
    "Elevated transaction amount for account profile",
    "Out-of-pattern transaction time flagged for review",
    "Dormant account reactivation",
    "Round-number transaction amount flagged for review",
]


def _ts(base: datetime, hours_offset: float) -> str:
    return (base + timedelta(hours=hours_offset)).isoformat()


def make_fixture_matched_structuring_scheme():
    """Hardcoded to match the pre-recorded case_001 fixtures exactly."""
    accounts = [(f"ACCT-{1001 + i}", f"Individual {1001 + i}", "personal", "") for i in range(12)]
    accounts.append(("ACCT-9000", "Coastline Catering Co.", "business", "Registered caterer, KYC on file since 2024."))
    accounts.append(("EXT-5000", "External account (unknown bank)", "external", ""))

    transactions = []
    alerts = []
    total = 0.0
    for i in range(12):
        amount = 9200 + i * 50
        total += amount
        txn_id = f"TXN-{i + 1:04d}"
        transactions.append((txn_id, f"ACCT-{1001 + i}", "ACCT-9000", amount, _ts(BASE_DATE, i * 3)))
        alerts.append((f"ALERT-{i + 1:04d}", f"ACCT-{1001 + i}", txn_id, "Sub-$10,000 transfer near CTR threshold", _ts(BASE_DATE, i * 3)))

    cashout_txn = "TXN-0013"
    transactions.append((cashout_txn, "ACCT-9000", "EXT-5000", round(total, 2), _ts(BASE_DATE, 40)))
    alerts.append(("ALERT-0013", "ACCT-9000", cashout_txn, "Large same-day consolidated outflow", _ts(BASE_DATE, 40)))

    return accounts, transactions, alerts


def make_structuring_scheme(acc_ctr, txn_ctr, alert_ctr, n_feeders: int, base: datetime):
    hub = f"ACCT-{next(acc_ctr)}"
    ext = f"EXT-{next(acc_ctr)}"
    accounts = [(hub, f"Business {hub}", "business", "")]
    accounts.append((ext, "External account", "external", ""))
    transactions, alerts = [], []
    total = 0.0
    for _ in range(n_feeders):
        feeder = f"ACCT-{next(acc_ctr)}"
        accounts.append((feeder, f"Individual {feeder}", "personal", ""))
        amount = random.uniform(8800, 9850)
        total += amount
        txn_id = f"TXN-{next(txn_ctr):04d}"
        ts = _ts(base, random.uniform(0, 40))
        transactions.append((txn_id, feeder, hub, round(amount, 2), ts))
        alerts.append((f"ALERT-{next(alert_ctr):04d}", feeder, txn_id, _reason_rng.choice(STRUCTURING_FEEDER_REASONS), ts))
    cashout_txn = f"TXN-{next(txn_ctr):04d}"
    ts = _ts(base, 44)
    transactions.append((cashout_txn, hub, ext, round(total, 2), ts))
    alerts.append((f"ALERT-{next(alert_ctr):04d}", hub, cashout_txn, _reason_rng.choice(STRUCTURING_CASHOUT_REASONS), ts))
    return accounts, transactions, alerts


def make_round_tripping_scheme(acc_ctr, txn_ctr, alert_ctr, cycle_len: int, base: datetime):
    ring = [f"ACCT-{next(acc_ctr)}" for _ in range(cycle_len)]
    accounts = [(a, f"Individual {a}", "personal", "") for a in ring]
    transactions, alerts = [], []
    amount = random.uniform(15000, 40000)
    for i in range(cycle_len):
        src, dst = ring[i], ring[(i + 1) % cycle_len]
        leg_amount = round(amount * random.uniform(0.9, 0.98), 2)  # slight "peeling" each hop
        txn_id = f"TXN-{next(txn_ctr):04d}"
        ts = _ts(base, i * 6)
        transactions.append((txn_id, src, dst, leg_amount, ts))
        alerts.append((f"ALERT-{next(alert_ctr):04d}", src, txn_id, _reason_rng.choice(ROUND_TRIPPING_REASONS), ts))
    return accounts, transactions, alerts


def make_mule_hub_scheme(acc_ctr, txn_ctr, alert_ctr, n_counterparties: int, base: datetime):
    hub = f"ACCT-{next(acc_ctr)}"
    accounts = [(hub, f"Individual {hub}", "personal", "Newly opened account, low expected activity per KYC.")]
    transactions, alerts = [], []
    for i in range(n_counterparties):
        cp = f"ACCT-{next(acc_ctr)}"
        accounts.append((cp, f"Individual {cp}", "personal", ""))
        amount = round(random.uniform(400, 3000), 2)
        txn_id = f"TXN-{next(txn_ctr):04d}"
        ts = _ts(base, i * 4)
        if i % 2 == 0:
            transactions.append((txn_id, cp, hub, amount, ts))
        else:
            transactions.append((txn_id, hub, cp, amount, ts))
        alerts.append((f"ALERT-{next(alert_ctr):04d}", hub, txn_id, _reason_rng.choice(MULE_HUB_REASONS), ts))
    return accounts, transactions, alerts


def make_benign_noise(acc_ctr, txn_ctr, alert_ctr, n_pairs: int, base: datetime):
    accounts, transactions, alerts = [], [], []
    for _ in range(n_pairs):
        a, b = f"ACCT-{next(acc_ctr)}", f"ACCT-{next(acc_ctr)}"
        accounts.append((a, f"Individual {a}", "personal", ""))
        accounts.append((b, f"Individual {b}", "personal", ""))
        amount = round(random.uniform(500, 8000), 2)
        txn_id = f"TXN-{next(txn_ctr):04d}"
        ts = _ts(base, random.uniform(0, 24 * 14))
        transactions.append((txn_id, a, b, amount, ts))
        alerts.append((f"ALERT-{next(alert_ctr):04d}", a, txn_id, _reason_rng.choice(BENIGN_REASONS), ts))
    return accounts, transactions, alerts


def generate():
    acc_ctr = itertools.count(2001)
    txn_ctr = itertools.count(14)
    alert_ctr = itertools.count(14)

    all_accounts, all_txns, all_alerts = make_fixture_matched_structuring_scheme()
    tenure_bias: dict[str, str | None] = {acc[0]: None for acc in all_accounts}

    for n_feeders in [6, 7, 9, 10]:
        a, t, al = make_structuring_scheme(acc_ctr, txn_ctr, alert_ctr, n_feeders, BASE_DATE + timedelta(days=random.randint(0, 10)))
        all_accounts += a; all_txns += t; all_alerts += al
        tenure_bias.update({acc[0]: None for acc in a})

    for cycle_len in [4, 5, 4, 5]:
        a, t, al = make_round_tripping_scheme(acc_ctr, txn_ctr, alert_ctr, cycle_len, BASE_DATE + timedelta(days=random.randint(0, 10)))
        all_accounts += a; all_txns += t; all_alerts += al
        tenure_bias.update({acc[0]: None for acc in a})

    for n_cp in [12, 16, 20]:
        a, t, al = make_mule_hub_scheme(acc_ctr, txn_ctr, alert_ctr, n_cp, BASE_DATE + timedelta(days=random.randint(0, 10)))
        all_accounts += a; all_txns += t; all_alerts += al
        tenure_bias.update({acc[0]: "short" for acc in a})

    a, t, al = make_benign_noise(acc_ctr, txn_ctr, alert_ctr, 90, BASE_DATE)
    all_accounts += a; all_txns += t; all_alerts += al
    tenure_bias.update({acc[0]: "long" for acc in a})

    profiles = []
    for account_id, _display_name, account_type, _kyc_notes in all_accounts:
        profile = make_profile(account_id, account_type, tenure_bias=tenure_bias.get(account_id))
        if profile is not None:
            profiles.append(profile)

    conn = connect()
    reset_case_data(conn)
    executemany(conn, "INSERT INTO accounts VALUES (?, ?, ?, ?)", all_accounts)
    executemany(conn, "INSERT INTO transactions VALUES (?, ?, ?, ?, ?)", all_txns)
    executemany(conn, "INSERT INTO alerts VALUES (?, ?, ?, ?, ?)", all_alerts)
    executemany(conn, PROFILE_INSERT_SQL, profiles)
    conn.close()

    print(f"Generated {len(all_accounts)} accounts, {len(all_txns)} transactions, {len(all_alerts)} alerts, {len(profiles)} client profiles.")


if __name__ == "__main__":
    generate()
