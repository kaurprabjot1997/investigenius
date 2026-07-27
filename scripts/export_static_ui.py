"""Exports a static, dependency-free HTML snapshot of the current app state
for sharing with teammates who aren't running the dev stack. Reads directly
from backend/investigenius.db and backend/cache/fixtures/ — the output is
plain HTML + inline SVG + one shared stylesheet, no JS, no server, no build
step. Just open static_ui/index.html in a browser.

Run from repo root: backend/.venv/Scripts/python.exe scripts/export_static_ui.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DB_PATH = BACKEND / "investigenius.db"
FIXTURES = BACKEND / "cache" / "fixtures"
OUT = ROOT / "static_ui"

sys.path.insert(0, str(BACKEND))
import networkx as nx  # noqa: E402

TYPOLOGY_LABEL = {
    "structuring": "Structuring",
    "round_tripping": "Round-tripping",
    "mule_hub": "Mule hub",
    "none": "No pattern",
}
TYPE_COLOR = {"business": "#0ea5e9", "personal": "#64748b", "external": "#dc2626"}
HUB_COLOR = "#b45309"

FEATURED_CASE_IDS = ["case_001", "case_005", "case_007", "case_013"]

# Inlined into every page's <head> rather than linked via <link href="styles.css">
# — a locked-down corporate browser (or a zip transfer that drops the
# sibling file, or Windows tagging extracted files with Mark-of-the-Web)
# can block a local file:// page from loading a *separate* local file as a
# resource. Inlining means each page is fully self-contained; nothing to
# transfer alongside it, nothing for a browser policy to block.
_CSS = (OUT / "styles.css").read_text(encoding="utf-8")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def risk_badge(score: float) -> str:
    variant = "badge-red" if score >= 70 else "badge-amber" if score >= 40 else "badge-slate"
    return f'<span class="badge {variant}">{score:.0f}</span>'


def verdict_badge(verdict: str) -> str:
    variant = {"escalate": "badge-red", "needs_review": "badge-amber", "close": "badge-emerald"}[verdict]
    return f'<span class="badge {variant}">{verdict.replace("_", " ").upper()}</span>'


def page(title: str, body: str, tag: str = "Static snapshot") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — InvestiGenius</title>
<style>
{_CSS}
</style>
</head>
<body>
<header>
  <span class="brand">InvestiGenius</span>
  <span class="snapshot-tag">{tag}</span>
</header>
{body}
<footer>Static snapshot generated from live dataset — not connected to a running backend. See TEAM_BRIEFING.md for the full write-up.</footer>
</body>
</html>"""


def svg_network(accounts: list[dict], transactions: list[dict]) -> str:
    graph = nx.DiGraph()
    for a in accounts:
        graph.add_node(a["account_id"])
    for t in transactions:
        graph.add_edge(t["from_account"], t["to_account"], amount=t["amount"])

    pos = nx.spring_layout(graph, seed=42, k=1.4 / max(len(graph.nodes) ** 0.5, 1))
    W, H, PAD = 680, 380, 40
    xs = [p[0] for p in pos.values()] or [0]
    ys = [p[1] for p in pos.values()] or [0]
    minx, maxx = min(xs), max(xs) or 1
    miny, maxy = min(ys), max(ys) or 1
    spanx = (maxx - minx) or 1
    spany = (maxy - miny) or 1

    def sx(x):
        return PAD + (x - minx) / spanx * (W - 2 * PAD)

    def sy(y):
        return PAD + (y - miny) / spany * (H - 2 * PAD)

    degrees = dict(graph.degree())
    hub_id = max(degrees, key=degrees.get) if degrees else None

    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
    account_type = {a["account_id"]: a["account_type"] for a in accounts}
    for t in transactions:
        x1, y1 = pos[t["from_account"]]
        x2, y2 = pos[t["to_account"]]
        parts.append(f'<line x1="{sx(x1):.1f}" y1="{sy(y1):.1f}" x2="{sx(x2):.1f}" y2="{sy(y2):.1f}" stroke="#cbd5e1" stroke-width="1.5" />')
    for node, (x, y) in pos.items():
        is_hub = node == hub_id and degrees.get(node, 0) > 2
        color = HUB_COLOR if is_hub else TYPE_COLOR.get(account_type.get(node, "personal"), "#64748b")
        r = 9 if is_hub else 5
        cx, cy = sx(x), sy(y)
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{color}" />')
        parts.append(f'<text x="{cx + r + 3:.1f}" y="{cy + 3:.1f}" font-size="9" fill="#475569" font-family="ui-monospace,monospace">{node}</text>')
    parts.append("</svg>")
    return "".join(parts)


def account_profile_table(accounts: list[dict]) -> str:
    rows = []
    for a in accounts:
        p = a.get("profile")
        if not p:
            continue
        tenure = f'{p["tenure_years"]}y' + (" · new to Canada" if p["new_to_canada_segment"] else "")
        residence = p["residence_country"] + (" (non-resident)" if p["non_resident_tax_flag"] else "")
        rows.append(
            f"<tr><td class='mono'>{a['account_id']}</td><td>{tenure}</td>"
            f"<td>{p['income_after_tax_range'] or '—'}</td><td>{p['occupation'] or '—'}</td>"
            f"<td>{residence}</td><td>{'Enrolled' if p['digital_enrolled'] else 'Not enrolled'}</td>"
            f"<td>{p['active_product_count']}</td></tr>"
        )
    if not rows:
        return ""
    return f"""<div class="info-banner">Client profile context below is mock UCP-style data (fabricated by the generator) — shown for investigator context, deliberately excluded from the automated risk score.</div>
<table class="card-table">
<thead><tr><th>Account</th><th>Tenure</th><th>Income</th><th>Occupation</th><th>Residence</th><th>Digital</th><th>Products</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>"""


def transactions_table(transactions: list[dict]) -> str:
    rows = "".join(
        f"<tr><td class='mono'>{t['txn_id']}</td><td class='mono'>{t['from_account']}</td>"
        f"<td class='mono'>{t['to_account']}</td><td>${t['amount']:.2f}</td><td>{t['ts']}</td></tr>"
        for t in transactions
    )
    return f"""<table class="card-table">
<thead><tr><th>Txn</th><th>From</th><th>To</th><th>Amount</th><th>Time</th></tr></thead>
<tbody>{rows}</tbody>
</table>"""


def playbook_section(playbook: list[dict]) -> str:
    if not playbook:
        return ""
    matched = sum(1 for p in playbook if p["matched"])
    rows = "".join(
        f"""<div class="audit-entry"><div class="top">
<strong>{'&#10003;' if p['matched'] else '&ndash;'} [{p['id']}] {p['criterion']}</strong>
</div><div class="actor">{p['evidence']}</div></div>"""
        for p in playbook
    )
    return f"""<div class="section-label">Standardized Investigation Playbook &mdash; {matched}/{len(playbook)} criteria matched</div>
<div class="card-table" style="padding:0">{rows}</div>"""


def signals_section(signals: list[dict]) -> str:
    if not signals:
        return """<div class="section-label">Automated Data Analysis</div>
<div class="info-banner">No behavioral anomalies detected against client profile data for this case.</div>"""
    rows = "".join(
        f"""<div class="audit-entry"><div class="top"><strong>{s['account_id']} &mdash; {s['label']}</strong></div>
<div class="actor">{s['detail']}</div></div>"""
        for s in signals
    )
    return f"""<div class="section-label">Automated Data Analysis &mdash; {len(signals)} signal(s) found</div>
<div class="card-table" style="padding:0">{rows}</div>"""


def argument_card(title: str, css_class: str, arg: dict) -> str:
    claims = "".join(
        f'<div class="claim">{c["statement"]}<span class="cite">{c["citation_id"]}</span></div>'
        for c in arg.get("claims", [])
    )
    return f"""<div class="arg-card {css_class}">
<h3>{title}</h3>
<p>{arg['summary']}</p>
{claims}
</div>"""


def investigation_section(fixture_prefix: str) -> str:
    def load(role):
        path = FIXTURES / f"{fixture_prefix}_{role}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    prosecutor, defense, adjudicator = load("prosecutor"), load("defense"), load("adjudicator")
    if not (prosecutor and defense and adjudicator):
        return '<div class="note-banner">No recorded AI investigation for this case in this snapshot — only case_001 has a pre-recorded fixture.</div>'

    verdict = adjudicator["content"]
    return f"""<div class="section-label">AI Investigation (cached fixture — recorded during development)</div>
<div class="verdict-row">
  {verdict_badge(verdict['verdict'])}
  <span>Confidence: {verdict['confidence'] * 100:.0f}%</span>
  <span class="badge badge-slate">Source: replayed (cached) response</span>
</div>
<div class="arg-grid">
{argument_card("Prosecutor", "prosecutor", prosecutor['content'])}
{argument_card("Defense", "defense", defense['content'])}
</div>
<div class="section-label">Draft narrative (for investigator review, not a final determination)</div>
<div class="narrative-box">{verdict['narrative']}</div>"""


def audit_section(case_id: str) -> str:
    conn = connect()
    rows = conn.execute(
        "SELECT action, actor, payload, timestamp, row_hash FROM audit_log WHERE case_id=? ORDER BY id ASC",
        (case_id,),
    ).fetchall()
    conn.close()
    if not rows:
        return '<div class="note-banner">No audit actions recorded for this case yet.</div>'
    entries = ""
    for r in rows:
        entries += f"""<div class="audit-entry">
  <div class="top"><strong>{r['action'].replace('_', ' ')}</strong><span>{r['timestamp']}</span></div>
  <div class="actor">by {r['actor']}</div>
  <pre>{json.dumps(json.loads(r['payload']), indent=2)}</pre>
  <div class="hash">hash: {r['row_hash']}</div>
</div>"""
    return f'<div class="card-table" style="padding:0">{entries}</div>'


# Reuses the live app's own query + playbook/signal computation (app/cases.py)
# rather than a second hand-written copy — a duplicate here is exactly how
# the round-tripping playbook bug slipped through undetected earlier: two
# implementations of "the same" logic silently drifting apart.
from app.cases import get_case_detail as _get_case_detail  # noqa: E402


def get_case_detail(conn: sqlite3.Connection, case_id: str) -> dict | None:
    return _get_case_detail(case_id)


def render_case_page(detail: dict) -> str:
    body = f"""<div class="container">
<a class="back-link" href="queue.html">&larr; Back to case queue</a>
<div class="page-header" style="margin-top:12px">
  <div>
    <h1 class="page-title">{detail['case_id']}</h1>
    <p class="page-sub">{TYPOLOGY_LABEL[detail['typology_guess']]} · risk {detail['risk_score']:.0f}/100 · {len(detail['accounts'])} accounts · {len(detail['alerts'])} alerts merged</p>
  </div>
  <a class="back-link" href="audit_{detail['case_id']}.html">View audit trail &rarr;</a>
</div>
<div class="graph-card">
{svg_network(detail['accounts'], detail['transactions'])}
<div class="legend">
  <span><i class="dot" style="background:#0ea5e9"></i>Business</span>
  <span><i class="dot" style="background:#64748b"></i>Personal</span>
  <span><i class="dot" style="background:#dc2626"></i>External</span>
  <span><i class="dot" style="background:#b45309"></i>Hub (highest degree)</span>
</div>
</div>
{account_profile_table(detail['accounts'])}
{signals_section(detail['behavioral_signals'])}
{transactions_table(detail['transactions'])}
{playbook_section(detail['playbook'])}
{investigation_section(detail['case_id'])}
</div>"""
    return page(detail["case_id"], body, tag=f"Case detail · {TYPOLOGY_LABEL[detail['typology_guess']]}")


def render_audit_page(case_id: str) -> str:
    body = f"""<div class="container">
<a class="back-link" href="{case_id}.html">&larr; Back to {case_id}</a>
<div class="page-header" style="margin-top:12px"><h1 class="page-title">Audit trail — {case_id}</h1></div>
{audit_section(case_id)}
</div>"""
    return page(f"Audit — {case_id}", body, tag="Hash-chained audit log")


def render_queue_page(cases: list[dict], featured_ids: set[str]) -> str:
    total_alerts = sum(c["alert_count"] for c in cases)
    reduction = round((1 - len(cases) / max(total_alerts, 1)) * 100)
    high_risk = [c for c in cases if c["risk_score"] >= 70]

    rows = []
    for c in cases:
        is_featured = c["case_id"] in featured_ids
        case_cell = f'<a href="{c["case_id"]}.html">{c["case_id"]}</a>' if is_featured else c["case_id"]
        row_class = ' class="linked"' if is_featured else ""
        rows.append(
            f"<tr{row_class}><td class='mono'>{case_cell}</td><td>{TYPOLOGY_LABEL[c['typology_guess']]}</td>"
            f"<td>{risk_badge(c['risk_score'])}</td><td>{c['account_count']}</td>"
            f"<td>{c['alert_count']}</td><td>{c['status']}</td></tr>"
        )

    body = f"""<div class="container">
<a class="back-link" href="index.html">&larr; Back to overview</a>
<div class="stat-grid" style="margin-top:16px">
  <div class="stat-tile"><div class="stat-label">Raw alerts</div><div class="stat-value">{total_alerts}</div></div>
  <div class="stat-tile"><div class="stat-label">Network cases</div><div class="stat-value">{len(cases)}</div><div class="stat-sub">{reduction}% reduction</div></div>
  <div class="stat-tile"><div class="stat-label">High-risk cases</div><div class="stat-value accent-red">{len(high_risk)}</div><div class="stat-sub">risk score &ge; 70</div></div>
</div>
<div class="info-banner">4 cases below are linked to full detail pages ({', '.join(sorted(featured_ids))}) — one per typology plus a benign example. The rest show real clustering output from this snapshot but weren't exported as individual pages.</div>
<table class="card-table">
<thead><tr><th>Case</th><th>Typology</th><th>Risk</th><th>Accounts</th><th>Alerts merged</th><th>Status</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</div>"""
    return page("Case queue", body, tag=f"{len(cases)} cases")


def render_index_page(cases: list[dict], featured_ids: list[str]) -> str:
    total_alerts = sum(c["alert_count"] for c in cases)
    links = "".join(f'<li><a href="{cid}.html">{cid} — {TYPOLOGY_LABEL[next(c["typology_guess"] for c in cases if c["case_id"]==cid)]}</a></li>' for cid in featured_ids)
    body = f"""<div class="container">
<div class="hero">
<h1>InvestiGenius — AML Investigation Copilot</h1>
<p>Static snapshot of the current build, generated from the live synthetic dataset ({total_alerts} alerts clustered into {len(cases)} network cases). No backend required to view — every page here is plain HTML with an inline SVG network graph. See <strong>TEAM_BRIEFING.md</strong> in this folder for the full write-up: what the app does, how it works, and what's next.</p>
</div>
<div class="section-label">Explore</div>
<ul class="link-list">
<li><a href="queue.html">Case queue — full clustered case list with risk scoring</a></li>
{links}
</ul>
</div>"""
    return page("Overview", body, tag="Snapshot home")


def main():
    conn = connect()
    cases = [dict(r) for r in conn.execute(
        """SELECT c.case_id, c.typology_guess, c.risk_score, c.status,
                  COUNT(DISTINCT ca.account_id) AS account_count,
                  COUNT(DISTINCT cal.alert_id) AS alert_count
           FROM cases c
           LEFT JOIN case_accounts ca ON ca.case_id=c.case_id
           LEFT JOIN case_alerts cal ON cal.case_id=c.case_id
           GROUP BY c.case_id ORDER BY c.risk_score DESC"""
    )]

    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(render_index_page(cases, FEATURED_CASE_IDS), encoding="utf-8")
    (OUT / "queue.html").write_text(render_queue_page(cases, set(FEATURED_CASE_IDS)), encoding="utf-8")

    for case_id in FEATURED_CASE_IDS:
        detail = get_case_detail(conn, case_id)
        (OUT / f"{case_id}.html").write_text(render_case_page(detail), encoding="utf-8")
        (OUT / f"audit_{case_id}.html").write_text(render_audit_page(case_id), encoding="utf-8")

    conn.close()
    print(f"Exported {2 + len(FEATURED_CASE_IDS) * 2} pages to {OUT}")


if __name__ == "__main__":
    main()
