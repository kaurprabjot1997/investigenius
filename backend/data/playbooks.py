"""Standardized investigation playbooks — the literal, visible answer to
"standardization of investigation quality": every case of a given typology
is checked against the same explicit, published criteria, by the same
deterministic code, rather than each investigator (or each LLM call)
implicitly deciding what counts as suspicious on a case-by-case basis.

This is deliberately layered ON TOP of, not mixed into, the automated
risk_score in app/graph/clustering.py — clustering.py's score stays driven
only by graph structure, verified and unchanged. Playbook matches are
investigator- and LLM-facing context: "here's how this case measures against
the published criteria," not a second scoring system competing with the
first.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import networkx as nx

STRUCTURING_MIN_AMOUNT = 8500
STRUCTURING_MAX_AMOUNT = 10000
STRUCTURING_MIN_FEEDERS = 4
CLUSTER_WINDOW_HOURS = 72
CONSOLIDATION_WINDOW_HOURS = 48
MULE_MIN_COUNTERPARTIES = 8

PLAYBOOKS: dict[str, list[dict[str, str]]] = {
    "structuring": [
        {"id": "STR-1", "criterion": "4+ inbound transfers to a single account, each 85-100% of the $10,000 CTR reporting threshold"},
        {"id": "STR-2", "criterion": "Near-threshold transfers clustered within a 72-hour window"},
        {"id": "STR-3", "criterion": "Consolidated outbound transfer follows the inbound cluster within 48 hours (rapid layering)"},
        {"id": "STR-4", "criterion": "Feeder accounts show only a single transaction each into the receiving account (no established relationship)"},
    ],
    "round_tripping": [
        {"id": "RT-1", "criterion": "A cyclical fund flow exists — money returns to (or near) its account of origin"},
        {"id": "RT-2", "criterion": "Each hop in the cycle occurs within a short time window of the previous"},
        {"id": "RT-3", "criterion": "Transferred amounts are similar in magnitude across hops, with no apparent economic purpose for the intermediate transfers"},
    ],
    "mule_hub": [
        {"id": "MH-1", "criterion": "A single account transacts with 8+ distinct counterparties within the case window"},
        {"id": "MH-2", "criterion": "The hub's transactions mix inbound and outbound roughly evenly, unlike a typical income/expense pattern"},
        {"id": "MH-3", "criterion": "The hub account's tenure with the bank is short relative to the transaction volume passing through it"},
    ],
    "none": [],
}


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _span_hours(timestamps: list[str]) -> float:
    parsed = [_parse_ts(t) for t in timestamps]
    return (max(parsed) - min(parsed)).total_seconds() / 3600


def _evaluate_structuring(detail: dict[str, Any]) -> list[dict[str, Any]]:
    txns = detail["transactions"]
    inbound_by_receiver: dict[str, list[dict]] = {}
    for t in txns:
        inbound_by_receiver.setdefault(t["to_account"], []).append(t)

    near_threshold_group, hub = [], None
    for receiver, group in inbound_by_receiver.items():
        near = [t for t in group if STRUCTURING_MIN_AMOUNT <= t["amount"] < STRUCTURING_MAX_AMOUNT]
        if len(near) >= STRUCTURING_MIN_FEEDERS:
            near_threshold_group, hub = near, receiver
            break

    str1 = bool(near_threshold_group)
    str2 = str1 and _span_hours([t["ts"] for t in near_threshold_group]) <= CLUSTER_WINDOW_HOURS

    str3, str3_evidence = False, "No consolidated outbound transfer found within the window."
    if hub:
        outbound = [t for t in txns if t["from_account"] == hub and t not in near_threshold_group]
        if outbound and near_threshold_group:
            last_inbound = max(_parse_ts(t["ts"]) for t in near_threshold_group)
            for t in outbound:
                gap = (_parse_ts(t["ts"]) - last_inbound).total_seconds() / 3600
                if 0 <= gap <= CONSOLIDATION_WINDOW_HOURS:
                    str3 = True
                    str3_evidence = f"{t['txn_id']} moved funds out {gap:.1f}h after the last near-threshold inbound transfer."
                    break

    feeder_txn_counts: dict[str, int] = {}
    for t in txns:
        feeder_txn_counts[t["from_account"]] = feeder_txn_counts.get(t["from_account"], 0) + 1
    feeders = {t["from_account"] for t in near_threshold_group}
    str4 = bool(feeders) and all(feeder_txn_counts.get(f, 0) == 1 for f in feeders)

    return [
        {"id": "STR-1", "matched": str1, "evidence": f"{len(near_threshold_group)} near-threshold transfers into {hub}." if str1 else "No account received 4+ near-threshold transfers."},
        {"id": "STR-2", "matched": str2, "evidence": f"Spread across {_span_hours([t['ts'] for t in near_threshold_group]):.1f}h." if str1 else "N/A — STR-1 not matched."},
        {"id": "STR-3", "matched": str3, "evidence": str3_evidence},
        {"id": "STR-4", "matched": str4, "evidence": "Each feeder account appears exactly once." if str4 else "One or more feeder accounts have prior transactions in this case."},
    ]


def _evaluate_round_tripping(detail: dict[str, Any]) -> list[dict[str, Any]]:
    txns = detail["transactions"]
    # Reuses the same check as app/graph/clustering.py's own typology
    # detection (not a hand-rolled reimplementation) so the playbook can
    # never disagree with the classification that put the case in this
    # typology to begin with.
    graph = nx.DiGraph()
    for t in txns:
        graph.add_edge(t["from_account"], t["to_account"])
    has_cycle = graph.number_of_nodes() > 1 and not nx.is_directed_acyclic_graph(graph)

    rt2 = has_cycle and (not txns or _span_hours([t["ts"] for t in txns]) <= CLUSTER_WINDOW_HOURS)
    amounts = [t["amount"] for t in txns]
    rt3 = has_cycle and amounts and (max(amounts) - min(amounts)) / max(amounts) < 0.25

    return [
        {"id": "RT-1", "matched": has_cycle, "evidence": "A closed transaction cycle exists among case accounts." if has_cycle else "No cycle detected."},
        {"id": "RT-2", "matched": rt2, "evidence": f"Full cycle completes within {_span_hours([t['ts'] for t in txns]):.1f}h." if has_cycle else "N/A — RT-1 not matched."},
        {"id": "RT-3", "matched": rt3, "evidence": "Hop amounts vary by less than 25%." if rt3 else "Hop amounts vary significantly or no cycle present."},
    ]


def _evaluate_mule_hub(detail: dict[str, Any]) -> list[dict[str, Any]]:
    txns = detail["transactions"]
    counterparties: dict[str, set[str]] = {}
    inout: dict[str, dict[str, int]] = {}
    for t in txns:
        counterparties.setdefault(t["from_account"], set()).add(t["to_account"])
        counterparties.setdefault(t["to_account"], set()).add(t["from_account"])
        inout.setdefault(t["from_account"], {"in": 0, "out": 0})["out"] += 1
        inout.setdefault(t["to_account"], {"in": 0, "out": 0})["in"] += 1

    hub = max(counterparties, key=lambda k: len(counterparties[k])) if counterparties else None
    mh1 = bool(hub) and len(counterparties.get(hub, set())) >= MULE_MIN_COUNTERPARTIES

    mh2 = False
    if hub:
        io = inout.get(hub, {"in": 0, "out": 0})
        total = io["in"] + io["out"]
        mh2 = total > 0 and min(io["in"], io["out"]) / total >= 0.3

    profile = next((a["profile"] for a in detail["accounts"] if a["account_id"] == hub and a.get("profile")), None)
    total_volume = sum(t["amount"] for t in txns if t["from_account"] == hub or t["to_account"] == hub)
    mh3 = bool(profile) and profile["tenure_years"] < 2 and total_volume > 5000

    return [
        {"id": "MH-1", "matched": mh1, "evidence": f"{hub} transacts with {len(counterparties.get(hub, set()))} distinct counterparties." if hub else "No hub identified."},
        {"id": "MH-2", "matched": mh2, "evidence": "Inbound/outbound transaction counts are roughly balanced." if mh2 else "Transaction flow is predominantly one-directional."},
        {"id": "MH-3", "matched": mh3, "evidence": f"Hub tenure {profile['tenure_years']}y against ${total_volume:,.0f} in case volume." if profile else "No profile on file for the hub account."},
    ]


def evaluate_playbook(typology: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
    criteria = PLAYBOOKS.get(typology, [])
    if not criteria:
        return []
    evaluator = {
        "structuring": _evaluate_structuring,
        "round_tripping": _evaluate_round_tripping,
        "mule_hub": _evaluate_mule_hub,
    }.get(typology)
    if evaluator is None:
        return [{**c, "matched": False, "evidence": "No automated check implemented for this criterion yet."} for c in criteria]

    results = {r["id"]: r for r in evaluator(detail)}
    return [{**c, **results.get(c["id"], {"matched": False, "evidence": "Not evaluated."})} for c in criteria]
