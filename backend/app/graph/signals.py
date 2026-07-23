"""Automated behavioral signal detection — the second half of "automatic
data analysis": beyond clustering *which accounts* form a network, this
looks *within* a case for transactional red flags using the client-profile
data (data/profiles.py), the way a real AML analyst cross-references income
and account-age against activity.

Deliberately built only on financial-capacity/behavioral fields (income
band, tenure, transaction volume) — never on the demographic/segmentation
fields (age, generation, new_to_canada_segment, etc.), consistent with
data/profiles.py's governance note. Also, like data/playbooks.py, this is
layered ON TOP of app/graph/clustering.py's risk_score, not merged into it —
that score stays driven only by graph structure.
"""
from __future__ import annotations

from typing import Any

INCOME_BAND_UPPER = {
    "<$20K": 20_000,
    "$20K-$40K": 40_000,
    "$40K-$60K": 60_000,
    "$60K-$80K": 80_000,
    "$80K-$120K": 120_000,
    "$120K+": 300_000,  # open-ended band; generous cap so this stays conservative
}
INCOME_MISMATCH_MULTIPLIER = 3
NEW_ACCOUNT_TENURE_YEARS = 1.0
NEW_ACCOUNT_VOLUME_THRESHOLD = 5_000


def _account_volume(account_id: str, transactions: list[dict]) -> float:
    return sum(t["amount"] for t in transactions if t["from_account"] == account_id or t["to_account"] == account_id)


def compute_behavioral_signals(detail: dict[str, Any]) -> list[dict[str, Any]]:
    signals = []
    for account in detail["accounts"]:
        profile = account.get("profile")
        if not profile:
            continue
        account_id = account["account_id"]
        volume = _account_volume(account_id, detail["transactions"])

        income_band = profile["income_after_tax_range"]
        upper = INCOME_BAND_UPPER.get(income_band)
        if upper and volume > upper * INCOME_MISMATCH_MULTIPLIER:
            signals.append({
                "account_id": account_id,
                "signal": "income_volume_mismatch",
                "label": "Transaction volume inconsistent with stated income",
                "detail": f"${volume:,.0f} transacted in this case vs. income band {income_band} (upper bound ${upper:,.0f}).",
            })

        if profile["tenure_years"] < NEW_ACCOUNT_TENURE_YEARS and volume > NEW_ACCOUNT_VOLUME_THRESHOLD:
            signals.append({
                "account_id": account_id,
                "signal": "new_account_high_volume",
                "label": "New account with disproportionate transaction volume",
                "detail": f"Account is {profile['tenure_years']} years old with ${volume:,.0f} transacted in this case.",
            })

    return signals
