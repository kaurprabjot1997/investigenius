# InvestiGenius — Team Briefing

**Case:** InvestiGenius for Anti-Money Laundering (AML) — Women in T&O Hackathon 2026
**This doc is for:** teammates catching up on what's built, how it works, and what's left. Pair it with the static preview in this folder (`index.html` — open it in a browser, no install needed).

---

## 1. The problem we're solving

The AML Investigation & Triage team gets a high volume of alerts, spends most of its time manually cross-referencing transaction data and customer profiles, and produces investigation quality that varies by investigator because there's no standardized process. The ask: use GenAI to streamline triage and investigation while keeping it consistent and audit-defensible.

## 2. Why our approach is different from "GenAI reads an alert and scores it"

Assume every other team pitches some version of "LLM scores each alert." That's the obvious reading of the brief, and it has a structural blind spot: real laundering schemes (structuring, round-tripping, mule networks) only become visible when you connect multiple accounts — scoring alerts one at a time can't see that.

**Our wedge: network-level triage, not alert-level triage.**

1. **Graph clustering first.** Before any LLM call, we build a transaction graph and group alerts by which accounts are actually connected — so 500 individual alerts might become 40 network cases. This is the headline number for the pitch: a real, measurable reduction, not just "AI made it faster."
2. **Adversarial multi-agent review, not a single guess.** For each case, three agents run: a **Prosecutor** (builds the case for suspicion), a **Defense** (actively looks for innocent explanations), and an **Adjudicator** (weighs both and issues a verdict with a full reasoning trail). This mirrors how good human investigation actually works, and it produces an audit-ready reasoning trail as a side effect — not just a score.
3. **A human always makes the final call.** The system drafts and recommends; nothing is ever auto-escalated or auto-closed without a person approving. That's a design commitment, not a limitation — it's the sentence that reassures a compliance-minded judge (or a real compliance team) more than anything else in the pitch.

## 3. How this maps to the brief's four named challenges

Worth having ready for the pitch — the brief names four challenges explicitly, and every one of them maps to a specific, demoable piece of the product, not just a slide claim:

| Brief challenge | What actually does it |
|---|---|
| **High volume of alerts** | Graph clustering collapses raw alerts into network cases before anything else happens — 205 alerts → 102 cases live, with the true schemes surfacing at the top. |
| **Manual data analysis** | Two automated layers replace manual cross-referencing: (1) the graph/typology detection itself, and (2) a new behavioral-signals layer that checks each account's transaction volume against its client-profile data (income band, tenure) and flags mismatches automatically — no investigator has to pull that comparison by hand. |
| **Standardization of investigation quality** | Two layers here too: (1) the Prosecutor/Defense/Adjudicator adversarial pipeline, which runs identically for every case, and (2) a new **investigation playbook** — a published, typology-specific checklist (e.g. 4 explicit criteria for structuring) that gets automatically checked against every case's real data, so "what counts as suspicious" is the same published rule set every time, not an implicit judgment call. |
| **Resource constraints** | Direct consequence of the above three — investigators spend time on the ~12 high-risk cases the system surfaces, not manually triaging all 102. |

## 4. What's built and verified working right now

- **Synthetic dataset generator** — plants realistic structuring, round-tripping, and mule-hub schemes plus benign noise transactions, with a fixed random seed so it's reproducible.
- **Network clustering engine** (NetworkX, connected components + cycle/degree detection) — turns raw alerts into risk-scored network cases. Verified live: **205 alerts → 102 cases**, with every planted scheme correctly surfaced at the top (risk 76–100) above 90 benign singleton cases (risk ~10).
- **Automated behavioral signals** *(new)* — flags accounts whose in-case transaction volume is inconsistent with their income band, or whose account is very new relative to the volume passing through it. Built only on financial-capacity fields (income, tenure) — never demographic ones — and verified firing correctly on real generated data (e.g. a mule-hub case: "0.9 years old, $28,647 transacted").
- **Investigation playbook** *(new)* — a published, per-typology checklist (4 criteria for structuring, 3 each for round-tripping and mule hub) that's automatically checked against each case's real data and shown as a pass/fail list. Reuses the same cycle-detection logic as the clustering engine itself, so the playbook can't disagree with the classification that put a case in that typology to begin with — we caught and fixed exactly that inconsistency during testing before it shipped.
- **Multi-agent investigation pipeline** — Prosecutor/Defense/Adjudicator, each constrained to structured JSON output (no free-text parsing), with a deterministic citation validator that checks every factual claim actually references a real transaction/account ID in the case — and auto-flags the case for mandatory human review if it doesn't, or if model confidence is low. The playbook and behavioral signals now feed into this pipeline's context too, giving the agents concrete standardized criteria to reference.
- **PII masking, RBAC, hash-chained audit log** — every investigation and human decision is logged immutably; each audit row embeds the hash of the previous row, so tampering is detectable, not just claimed.
- **Full frontend** — Case Queue (risk-sorted, reduction stat), Case Detail (network graph visualization, transaction table, client profile panel, automated signals, investigation playbook), Investigation panel (agent reasoning trace, editable draft narrative, approve/reject), Audit Trail view.
- **Client profile enrichment** — modeled on RBC's real UCP4.0 data-dictionary field categories (tenure, income/credit bands, digital-channel engagement, occupation, residency, product holdings, segmentation codes) using entirely fabricated values — no real client data was used anywhere. Deliberately **not** fed into the automated risk score (only real transaction-graph structure drives that) — segmentation/demographic fields are shown to investigators as context only. That split is a real fair-lending/model-risk consideration, and it's enforced in the code, not just a talking point. The two new behavioral signals are the one deliberate exception — income and tenure are financial-capacity signals, not demographic proxies, so they're allowed to be genuine detection inputs (surfaced separately from the graph risk score, never blended into it).
- **Works with zero live LLM access.** Every agent call goes through a swappable interface — live Anthropic API, a stub for the bank's enterprise gateway, or a cached-replay mode that runs the entire pipeline off responses recorded earlier. This matters concretely: we don't yet have confirmed LLM API access on the bank laptop for hackathon day, so the whole demo is built to run convincingly with zero network dependency if it comes to that.

## 5. How it works (plain-language walkthrough)

```
Raw alerts + transactions + accounts
        │
        ▼
Graph clustering (NetworkX)  →  groups connected accounts into "network cases",
                                  guesses a typology (structuring / round-tripping /
                                  mule hub), assigns a risk score from graph
                                  structure alone
        │
        ▼
Investigator opens a case in the Case Queue → sees the network graph,
transaction table, and client profile context
        │
        ▼
Behavioral signals + playbook check run automatically  →  income/tenure
        mismatches flagged, typology-specific checklist scored against
        real case data — both shown before any LLM call happens
        │
        ▼
Clicks "Run investigation" →  PII gets masked  →  Prosecutor + Defense agents
                                run in parallel (with playbook/signal context
                                available to cite)  →  Adjudicator weighs
                                both  →  citation validator checks every
                                claim against real case data  →
                                low-confidence or uncited claims force
                                "needs review" regardless of what the model
                                said
        │
        ▼
Investigator reviews the draft narrative, edits it, approves or rejects  →
every action is written to the hash-chained audit log
```

## 6. Tech stack (deliberately minimal)

We cut every piece of infrastructure that didn't directly serve the demo:

- **Backend:** FastAPI, plain async Python (no LangChain/LangGraph — three fixed pipeline steps don't need an orchestration framework), SQLite (no Postgres/Docker), NetworkX for graph analytics, in-house RAG-lite (no vector DB), all pinned to specific package versions and checked with `pip-audit`/`npm audit`.
- **Frontend:** Vite + React + TypeScript, Tailwind, `react-force-graph-2d` for the network visualization.
- **Runs entirely on localhost** for the live demo — nothing depends on a cloud service beyond the LLM call itself, which is exactly the piece we've made swappable/optional (see above).

## 7. What's next

Rough mapping against the original 7-day plan — we're currently ahead of where a strict day-by-day pace would put us (dataset, graph layer, agent pipeline, guardrails, the full frontend, and both new analysis/standardization features are all done; the original plan had the frontend alone as a Day 5 task):

- [ ] **Record LLM fixtures for more demo cases — blocked on a credential, not on work.** Right now only `case_001` has a full cached investigation. `scripts/record_fixtures.py` is written and ready — it drives the real pipeline against the live Anthropic API and defaults to our 4 featured cases (`case_001`, `case_005`, `case_007`, `case_013`). Whoever has API access: set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...` in `backend/.env`, run the script, then set `LLM_PROVIDER` back to `cache` before zipping for the bank laptop. (Along the way we found and fixed a real bug: `.env` was never actually being loaded by the app — it silently worked only because the default matched — so this now genuinely works, not just in theory.)
- [ ] **Confirm bank-laptop LLM access.** Ask hackathon organizers about a sanctioned sandbox/gateway; if nothing materializes, we present entirely in cached-replay mode — which the architecture already supports natively, not as a fallback bolted on late.
- [ ] **Stretch goal (if time allows): blind-spot red-team agent** — generates synthetic transaction patterns matching known typologies our current rules don't cover, and reports the gap. Biggest remaining "nobody else will have built this" feature.
- [ ] **Polish pass:** empty/loading states, visual QA, one-page model card (model used, limitations, human-oversight points — cheap, high credibility with judges).
- [ ] **Pitch prep:** lock the exact demo case(s), rehearse against the time limit, record a backup video in case live demo/wifi fails.

## 8. How to look at this yourself

- **No install needed:** open `static_ui/index.html` in any browser. It's a snapshot of the real generated dataset (not mockups) — case queue, network graphs, automated signals, investigation playbooks, and the one full AI investigation trace we've recorded so far.
- **To run the real, live app:** see `README.md` at the project root for setup (`backend/` FastAPI + `frontend/` Vite React).
