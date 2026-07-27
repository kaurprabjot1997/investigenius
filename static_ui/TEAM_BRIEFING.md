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

## 5. Product experience: sign-in, RBC branding, a more interactive UI

- **Sign-in screen** *(new)* — a branded "advisor journey" entry point: pick a persona (Alex Chen, Junior AML Investigator / Priya Sharma, Senior AML Investigator / Morgan Lee, Compliance Officer) instead of landing directly on the dashboard. It's explicitly labeled as a demo sign-in, not real authentication — the actual role enforcement is unchanged and still happens server-side (`_require_role` in `routes.py`). This is cosmetic narrative polish, not a scope change to the security model, and it's stated as such on-screen so nobody mistakes it for more than it is.
- **RBC-inspired branding** *(new)* — a blue/gold theme (`tailwind.config.js`) applied to the header, sign-in screen, and primary actions. Important caveat: these are plausible approximations, not verified against actual RBC brand guidelines (hex codes, exact typography) — swap in the real values if/when someone has access to them. No logo asset is used anywhere (nothing to fabricate a trademarked mark from) — it's a text wordmark only.
- **Sortable/filterable Case Queue** *(new)* — click any column header to sort, filter by typology, free-text search by case ID, and click the "High-risk cases" stat tile to filter to just those — turns the queue from a static table into an actual triage tool.
- **Staged investigation reveal** *(new)* — clicking "Run investigation" now shows the Prosecutor → Defense → Adjudicator sequence progressing live rather than a single spinner-then-dump. This is an honest staging, not decoration: the agents genuinely do run in that order server-side (Prosecutor+Defense in parallel, then Adjudicator) — the UI reveal just matches reality instead of hiding it behind a blank wait.

## 6. Precedent chat & the knowledge feedback loop

Directly answers "if an advisor is stuck on an unusual case, can they draw on what we learned from past cases" — and the mechanism that keeps that knowledge growing as the team works.

**How the knowledge base gets built (the feedback loop):** two write points, both already wired into the existing endpoints — no separate data-entry step for investigators:
1. Every time `/investigate` runs, the AI's grounded argument (verdict, confidence, narrative, key claims) gets written to a new `knowledge_entries` table.
2. Every time a human clicks Approve/Reject, their actual decision and notes get written too — including the valuable case where a human *overrides* the AI ("model said escalate, senior investigator rejected because X"). That override signal is the real feedback loop, not just an AI-generated summary talking to itself.

This is a deliberately separate table from the hash-chained `audit_log`, not an extension of it — `audit_log` is the compliance-critical, tamper-evident record of what happened and who signed off, which is exactly what a hash chain is for. `knowledge_entries` is a derived search index that exists to make investigators faster; it's disposable and re-derivable, so it doesn't need (or want) hash-chaining overhead. Neither table is ever wiped when the dataset regenerates.

**How retrieval works:** local TF-IDF cosine similarity computed with numpy (already a declared dependency — this is the first code that actually uses it), plus a same-typology boost. Deliberately *not* a third-party embeddings API: for a knowledge base of a dozen-ish cases, an embeddings API would mean a new credential and a new offline-availability risk stacked on top of the LLM-access uncertainty this whole project is already built around avoiding, for a quality difference that wouldn't be visible in a demo. Retrieval itself never touches an LLM or needs a cache fixture — only the final answer-composition call does, so search never breaks offline.

**How it stays honest:** the answer is generated only from the current case's context and whatever precedents retrieval actually found — if nothing relevant exists yet, the model is told the knowledge base is empty and instructed to say so rather than invent a precedent. Every citation is checked against the precedent set actually shown to the model; an unverified one is flagged inline in the UI rather than silently trusted.

**Offline-demo support:** a curated set of suggested questions per typology (e.g. "Have we seen a case like this before?") have their own recordable fixtures via `scripts/record_chat_fixtures.py` — same self-recording pattern as the main investigation pipeline. Free-text questions still work when there's live API access, and degrade with a clear "try a suggested question instead" message when there isn't, rather than a raw error.

## 7. How it works (plain-language walkthrough)

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

## 8. Tech stack (deliberately minimal)

We cut every piece of infrastructure that didn't directly serve the demo:

- **Backend:** FastAPI, plain async Python (no LangChain/LangGraph — the investigation and chat pipelines are fixed sequences that don't need an orchestration framework), SQLite (no Postgres/Docker), NetworkX for graph analytics, local TF-IDF/numpy for precedent retrieval (no vector DB, no embeddings API), all pinned to specific package versions and checked with `pip-audit`/`npm audit`.
- **Frontend:** Vite + React + TypeScript, Tailwind (now with an RBC-inspired theme extension), `react-force-graph-2d` for the network visualization.
- **Runs entirely on localhost** for the live demo — nothing depends on a cloud service beyond the LLM call itself, which is exactly the piece we've made swappable/optional (see above), for both the investigation pipeline and precedent chat.

## 9. What's next

Rough mapping against the original 7-day plan — we're currently ahead of where a strict day-by-day pace would put us:

- [ ] **Record LLM fixtures — blocked on a credential, not on work.** Two scripts are written and ready: `scripts/record_fixtures.py` (investigation fixtures for `case_001`, `case_005`, `case_007`, `case_013`) and `scripts/record_chat_fixtures.py` (precedent-chat fixtures for the suggested questions). **Ordering matters**: run `record_fixtures.py` first (it now also populates the knowledge base as a side effect), then click Approve/Reject by hand on a few cases in the running app — varied typologies, at least one reject — so there's real precedent data to retrieve, *then* run `record_chat_fixtures.py`. Recording chat fixtures against an empty knowledge base just bakes in weak "no precedent found" answers. Whoever has API access: set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...` in `backend/.env`, run both scripts in that order, then set `LLM_PROVIDER` back to `cache` before zipping for the bank laptop.
- [ ] **Confirm bank-laptop LLM access.** Ask hackathon organizers about a sanctioned sandbox/gateway; if nothing materializes, we present entirely in cached-replay mode — which the architecture already supports natively, not as a fallback bolted on late.
- [ ] **Stretch goal (if time allows): blind-spot red-team agent** — generates synthetic transaction patterns matching known typologies our current rules don't cover, and reports the gap. Biggest remaining "nobody else will have built this" feature.
- [ ] **Get real RBC brand values** if anyone has access to actual guidelines (hex codes, logo usage rules) — swap into `frontend/tailwind.config.js`.
- [ ] **Polish pass:** empty/loading states, visual QA, one-page model card (model used, limitations, human-oversight points — cheap, high credibility with judges).
- [ ] **Pitch prep:** lock the exact demo case(s) and suggested chat questions, rehearse against the time limit, record a backup video in case live demo/wifi fails.

## 10. How to look at this yourself

- **No install needed:** open `static_ui/index.html` in any browser. It's a snapshot of the real generated dataset (not mockups) — case queue, network graphs, automated signals, investigation playbooks, and the one full AI investigation trace we've recorded so far. (The sign-in screen and precedent chat are interactive features that need the live app — not reflected in this static snapshot.)
- **To run the real, live app:** see `README.md` at the project root for setup (`backend/` FastAPI + `frontend/` Vite React).
