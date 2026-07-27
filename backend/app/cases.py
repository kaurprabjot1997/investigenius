"""Read-side queries over the clustered case data — list/detail for the API,
and the narrative-building step that feeds the /investigate pipeline.
"""
from __future__ import annotations

from app.db import connect
from app.graph.signals import compute_behavioral_signals
from data.playbooks import evaluate_playbook

_PROFILE_FIELDS = [
    "age_range", "generation", "tenure_years", "income_after_tax_range", "credit_score_range",
    "occupation", "residence_country", "non_resident_tax_flag", "new_to_canada_segment",
    "digital_enrolled", "digital_active_ind", "mobile_auth_ind", "active_product_count",
    "total_relationship_balance", "profitability_segment", "vulnerability_segment",
    "wallet_band_segment", "client_product_segment", "staff_flag",
]

_ACCOUNT_WITH_PROFILE_SQL = (
    "SELECT a.account_id AS account_id, a.display_name, a.account_type, a.kyc_notes, "
    "p.account_id AS profile_account_id, " + ", ".join(f"p.{f}" for f in _PROFILE_FIELDS) +
    " FROM accounts a LEFT JOIN client_profiles p ON p.account_id = a.account_id"
)


def _split_account_and_profile(row) -> dict:
    # dict(row) would silently collide on the duplicate 'account_id' column
    # from the join — explicit aliasing above plus this manual split avoids
    # that, since a NULL profile.account_id (accounts with no UCP record,
    # e.g. external accounts) would otherwise clobber the real account_id.
    data = dict(row)
    has_profile = data.pop("profile_account_id") is not None
    profile = {f: data.pop(f) for f in _PROFILE_FIELDS}  # always pop, even if unused, so fields never leak to top level
    data["profile"] = profile if has_profile else None
    return data


def list_cases() -> list[dict]:
    conn = connect()
    rows = conn.execute(
        """
        SELECT c.case_id, c.typology_guess, c.risk_score, c.status,
               COUNT(DISTINCT ca.account_id) AS account_count,
               COUNT(DISTINCT cal.alert_id) AS alert_count
        FROM cases c
        LEFT JOIN case_accounts ca ON ca.case_id = c.case_id
        LEFT JOIN case_alerts cal ON cal.case_id = c.case_id
        GROUP BY c.case_id
        ORDER BY c.risk_score DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_alerts() -> list[dict]:
    """The raw alerts queue — every alert as it looked before graph
    clustering ever ran, plus which case it ended up merged into. This is
    what "high volume of alerts" actually looks like prior to automated
    analysis; app/graph/clustering.py is what turns this into list_cases().
    """
    conn = connect()
    rows = conn.execute(
        """
        SELECT al.alert_id, al.account_id, al.txn_id, al.reason, al.raised_at,
               ca.case_id, c.typology_guess, c.risk_score
        FROM alerts al
        LEFT JOIN case_alerts ca ON ca.alert_id = al.alert_id
        LEFT JOIN cases c ON c.case_id = ca.case_id
        ORDER BY al.raised_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_case_detail(case_id: str) -> dict | None:
    conn = connect()
    case = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if case is None:
        conn.close()
        return None

    account_ids = [r["account_id"] for r in conn.execute(
        "SELECT account_id FROM case_accounts WHERE case_id = ?", (case_id,)
    )]
    placeholders = ",".join("?" * len(account_ids))
    account_rows = conn.execute(
        f"{_ACCOUNT_WITH_PROFILE_SQL} WHERE a.account_id IN ({placeholders})",
        account_ids,
    ).fetchall() if account_ids else []
    accounts = [_split_account_and_profile(r) for r in account_rows]
    transactions = conn.execute(
        f"""SELECT * FROM transactions
            WHERE from_account IN ({placeholders}) OR to_account IN ({placeholders})""",
        account_ids + account_ids,
    ).fetchall() if account_ids else []
    alerts = conn.execute(
        """SELECT a.* FROM alerts a
           JOIN case_alerts ca ON ca.alert_id = a.alert_id
           WHERE ca.case_id = ?""",
        (case_id,),
    ).fetchall()
    conn.close()

    detail = {
        "case_id": case["case_id"],
        "typology_guess": case["typology_guess"],
        "risk_score": case["risk_score"],
        "status": case["status"],
        "accounts": accounts,
        "transactions": [dict(r) for r in transactions],
        "alerts": [dict(r) for r in alerts],
    }
    # Both layered on top of, not merged into, the risk_score computed in
    # app/graph/clustering.py — see data/playbooks.py and app/graph/signals.py
    # for why that separation is deliberate.
    detail["playbook"] = evaluate_playbook(detail["typology_guess"], detail)
    detail["behavioral_signals"] = compute_behavioral_signals(detail)
    return detail


def build_case_context(case_id: str) -> tuple[str, list[str]] | None:
    """Renders the case's accounts/transactions/alerts into the plain-text
    context handed to the LLM pipeline, plus the set of record IDs a citation
    is allowed to reference — anything outside this set fails the pipeline's
    citation validator.
    """
    detail = get_case_detail(case_id)
    if detail is None:
        return None

    lines = [f"Network case {case_id} — typology guess: {detail['typology_guess']}, graph risk score: {detail['risk_score']}/100.", "", "Accounts:"]
    for acct in detail["accounts"]:
        line = f"  {acct['account_id']} — {acct['display_name']} ({acct['account_type']}). KYC notes: {acct['kyc_notes'] or 'none on file'}."
        profile = acct.get("profile")
        if profile:
            # Only the fields with plausible AML relevance go into the LLM
            # context (tenure/income/digital-engagement/residency) — the
            # rest of the profile (segmentation codes, etc.) is shown to the
            # investigator in the UI but deliberately left out of the prompt,
            # consistent with data/profiles.py's governance note.
            line += (
                f" Client profile: tenure {profile['tenure_years']} years, "
                f"income {profile['income_after_tax_range'] or 'n/a'}, "
                f"occupation {profile['occupation'] or 'n/a'}, "
                f"residence {profile['residence_country']}, "
                f"digital banking enrolled: {'yes' if profile['digital_enrolled'] else 'no'}."
            )
        lines.append(line)
    lines.append("")
    lines.append("Transactions:")
    for txn in detail["transactions"]:
        lines.append(f"  {txn['txn_id']}: {txn['from_account']} -> {txn['to_account']}, ${txn['amount']:.2f}, {txn['ts']}.")
    lines.append("")
    lines.append("Alerts raised:")
    for alert in detail["alerts"]:
        lines.append(f"  {alert['alert_id']} on {alert['account_id']}: {alert['reason']} (txn {alert['txn_id']}).")

    if detail["playbook"]:
        lines.append("")
        lines.append(f"Standardized {detail['typology_guess']} playbook criteria (apply the same checklist every case of this typology is checked against):")
        for item in detail["playbook"]:
            status = "MATCHED" if item["matched"] else "not matched"
            lines.append(f"  [{item['id']}] {item['criterion']} — {status}. {item['evidence']}")

    if detail["behavioral_signals"]:
        lines.append("")
        lines.append("Automated behavioral signals (from transaction volume vs. client profile data):")
        for sig in detail["behavioral_signals"]:
            lines.append(f"  {sig['account_id']}: {sig['label']} — {sig['detail']}")

    record_ids = (
        [a["account_id"] for a in detail["accounts"]]
        + [t["txn_id"] for t in detail["transactions"]]
        + [a["alert_id"] for a in detail["alerts"]]
    )
    return "\n".join(lines), record_ids
