# InvestiGenius — Judge Q&A Prep

Anticipated questions grouped by the judging criteria they most likely come from, so you can weight rehearsal time the same way the score is weighted. Answers are written to be *said*, not read — keep them to a breath, then stop; let a follow-up question pull out more depth rather than front-loading everything.

**General rule for all of these: if you don't know, say "that's the right next question — here's how we'd validate that" rather than guessing.** This project's whole design philosophy is "don't claim what you can't back up" (that's literally what the citation validator enforces on the AI). Answering judges the same way is consistent, not evasive.

---

## Creativity & Innovation (30%)

**Q: Isn't this just an LLM reading alerts? What's actually novel here?**
The LLM is the smallest part of the innovation. The real wedge is upstream of any model call: graph clustering groups 205 raw alerts into 102 network cases by shared accounts, deterministically, before a single token is generated. Then instead of one model producing a score, three agents run an adversarial process — Prosecutor, Defense, Adjudicator — the way a real investigation actually works.

**Q: Why network/graph clustering instead of scoring each alert individually?**
Because structuring, round-tripping, and mule-hub schemes are structural patterns across multiple accounts — they're invisible one alert at a time by definition. An alert-by-alert scorer, AI or not, is reading one page of a story that spans twelve. Clustering first means the expensive reasoning (the LLM) only gets spent on cases that survived a real structural signal, not on every alert.

**Q: Why an adversarial multi-agent pattern instead of one well-prompted model call?**
A single model producing a verdict has no built-in mechanism to argue against itself — it just picks a plausible-sounding answer. Prosecutor and Defense run in parallel over the same case data with opposite briefs, so the counter-argument a real investigator would have to consider is surfaced structurally, not left to chance in a prompt. The Adjudicator only ever sees both sides before ruling.

**Q: Couldn't you get the same result with one really good prompt?**
You'd get an answer, but you couldn't verify it the same way. Separating the roles means each output is independently checked — citations validated against real record IDs, confidence gated, flagged for review if either check fails. Collapsing that into one call collapses the places where you can catch the model being wrong.

**Q: What's the "blind spot" you keep referencing in the obvious approach?**
Scoring alerts individually can't see relationships between accounts. A structuring scheme might spread nine deposits across three "unrelated" accounts, each individually unremarkable. Only when you connect the accounts does the pattern exist at all — that connection step is graph analytics, not GenAI, and it has to happen first.

---

## Solution Design & Implementation (25%)

**Q: Why FastAPI + SQLite instead of a "real" production stack?**
Because this is a one-week build, not a production deployment, and we didn't want to fake maturity we didn't have. FastAPI as a modular monolith means one deployable, no network hops between services. SQLite means no database server to install or explain to IT on a locked-down laptop — it regenerates deterministically from a fixed random seed on every clone. Both are documented, deliberate scope decisions, not shortcuts we're hiding.

**Q: Why NetworkX instead of a graph database like Neo4j?**
The actual question we needed answered is "which accounts are linked" — weakly-connected components answers that directly. A graph database earns its cost at a scale and query complexity we don't have yet. Reaching for Neo4j here would have been infrastructure for its own sake.

**Q: Why not LangChain or LangGraph to orchestrate the agents?**
The pipeline is a fixed sequence — Prosecutor and Defense in parallel, then Adjudicator — implemented directly in async Python with `asyncio.gather`. A framework earns its keep when orchestration is dynamic or the graph of calls changes at runtime; ours doesn't, so the framework would be pure overhead and one more dependency to secure and explain.

**Q: How do you guarantee the LLM's output is actually structured and usable?**
Every agent call uses forced tool-use — the model must return JSON matching a schema, never free text we'd have to parse. If a response is missing a required field (which does happen occasionally), the client retries up to three times with required-field validation before it ever accepts or caches a response. It never silently accepts malformed output.

**Q: How do you stop the model from inventing evidence?**
Every claim the agents make must cite a real record ID — a transaction, account, or profile ID that actually exists in that case's own data. A deterministic validator checks every citation in code after the model responds; nothing is trusted from the prose itself.

**Q: What happens when confidence is low or a citation doesn't check out?**
The case is automatically flagged `needs_review` and cannot be auto-closed or auto-escalated — it requires a human decision either way. That gate is a hard rule in code, not a suggestion to the model.

**Q: Is there a human in the loop, or does this auto-execute anything?**
Nothing auto-executes, ever. A human — senior investigator or compliance officer — has to explicitly approve or reject before anything is final, and that action is what writes to the audit log.

**Q: How is this secured? What about PII?**
Every string reaches PII masking (regex-based tokenization) before it goes anywhere near an LLM call, regardless of which provider is behind the abstraction, and it's unmasked again only for display. It's not Presidio or an ML detector — a hackathon-scope regex layer, but one that's auditable line by line rather than trusted to a black box.

**Q: What's the audit trail? Could someone alter a record after the fact?**
Every investigation and every human decision writes to a hash-chained log — each entry's hash includes the previous entry's hash, SHA-256. Altering any past entry breaks the chain from that point forward, which is checkable. That's tamper-evident by construction, not by policy.

**Q: Why not a vector database for the precedent search?**
The knowledge base uses local TF-IDF plus cosine similarity with a same-typology boost — no embeddings API, no per-query cost, no external dependency. It's deliberately not hash-chained like the audit log either, because it needs to stay searchable and mutable, not tamper-evident; those are different guarantees and we didn't want one table doing both jobs.

**Q: How does RBAC actually work — is it just a UI dropdown?**
No — role comes from whichever persona a user signs in as, and it's enforced server-side on every request via `_require_role()`, checked against an `X-Demo-Role` header. The sign-in screen itself is a cosmetic persona picker, not a full session/auth system, and we say that plainly rather than implying otherwise — faking real auth in a demo is worse than admitting it's simplified.

**Q: How would this scale to real bank alert volume?**
Clustering and behavioral signals are cheap deterministic operations that scale roughly linearly with alert count — the LLM only touches the cases that survive that filter. SQLite is the piece that would need to change first at real scale (to Postgres or similar); that's explicitly in the proposed roadmap, not something we're pretending isn't a gap.

---

## GenAI Leverage & Application (20%)

**Q: How many agents actually call an LLM, and how do they interact?**
Four: Prosecutor and Defense run in parallel over the same case data with opposing briefs, Adjudicator synthesizes both into a verdict with a confidence score and citations, and Precedent Chat is a separate, single-turn agent for institutional-memory questions.

**Q: Are Prosecutor and Defense really independent, or the same prompt run twice?**
Different prompts, different roles, same underlying case data — one is instructed to build the strongest case for suspicion, the other to actively find the legitimate explanation. They run concurrently and neither sees the other's output before producing its own.

**Q: What stops the Adjudicator from just agreeing with whichever argument sounds more confident?**
Nothing stops it from being wrong sometimes — that's exactly why the citation validator and confidence gate exist downstream of it. The architecture doesn't assume the Adjudicator is infallible; it assumes it needs to be checked, which is why an unverifiable claim gets flagged instead of trusted.

**Q: What's "forced tool-use" and why does it matter here?**
It means the model is required to return a structured JSON object matching a schema — not a paragraph we'd have to parse with regex or a second LLM call. That's what makes citation validation and confidence gating possible in the first place; you can't deterministically check prose.

**Q: Is Precedent Chat a general chatbot bolted onto the app?**
No — it's deliberately narrow. It only searches *other* cases' recorded findings and decisions, never the case currently open, and it's single-turn by design (no conversation history) to keep its behavior predictable and its fixture-recording surface bounded.

**Q: How does the feedback loop actually work — does the model get retrained?**
No retraining. Every investigation and every human approve/reject decision — including overrides — writes a searchable entry into the knowledge base. Precedent Chat's search pool grows every time the team works a case; the model itself is unchanged, but what it can retrieve gets richer over time.

**Q: What happens with zero internet or API access — does the demo just break?**
No — that scenario is a first-class path, not a fallback bolted on late. A provider-agnostic `LLMClient` interface sits behind every agent call; the Cached Replay implementation replays fixtures recorded from real calls during development, with zero network dependency. Same UI, same verdicts, same citations either way.

**Q: How do you stop the LLM from hallucinating?**
Layered defenses, not one trick. First, context grounding — the agents only ever see this specific case's real accounts, transactions, and alerts as provided context; they're reasoning over data we hand them, not recalling facts from training memory, which removes most of the opportunity for hallucination before it can happen. Second, forced tool-use means every claim has to come with a citation ID, not just a confident-sounding sentence. Third, a deterministic validator checks every citation against real record IDs in that case's own data after the model responds — a citation to a transaction that doesn't exist gets caught in code, never trusted from the prose. Fourth, a failed citation or low confidence auto-flags the case for mandatory human review instead of auto-deciding anything. Precedent Chat follows the same principle — it's TF-IDF retrieval over real recorded case entries, not the model "remembering" a similar past case from nowhere. We're not claiming zero hallucination at the model level; we're claiming it gets caught structurally before it reaches a decision.

---

## Intuition & User-Friendly Design (15%)

**Q: If a human still has to review every verdict, what did the AI actually save?**
Everything before that point: 103 fewer alerts to even open, a pre-built network graph, both sides of the argument already drafted with citations, and a checked-and-flagged verdict to react to instead of a blank page. The human's job shifts from investigating from zero to reviewing a well-formed case — that's the time savings, not removing the human.

**Q: How did you design for an actual investigator, not just developers?**
Two deliberately separate panels make the distinction explicit in the UI itself: "This case's evidence only" for the investigation panel, "Institutional memory" for precedent chat — so it's never ambiguous which one an investigator is looking at. The network graph is hover-to-trace and click-to-inspect rather than a static image, and the playbook applies the same published criteria every time, so quality doesn't depend on who's working the case.

**Q: Is the sign-in screen real authentication?**
No, and we don't claim it is — it's a persona picker so the demo can show how the experience differs for a junior investigator versus a senior investigator versus a compliance officer. The actual access control is enforced server-side regardless of what the UI shows.

**Q: Why both an Alerts Queue and a Case Queue — isn't that redundant?**
They answer different questions. Alerts Queue is the literal, un-clustered inbox — it makes "high volume of alerts" from the brief concrete instead of a slide claim. Case Queue is what it becomes after clustering. Showing both, side by side, *is* the answer to "how does the AI build a case from alerts."

---

## Potential Impact (10%)

**Q: What's the actual measurable impact?**
The one number we can defend precisely: 205 alerts cluster into 102 cases automatically, a 50% reduction in what needs individual attention, with 12 flagged high-risk. From there, at roughly 15 minutes of manual triage per alert, the 103 alerts that never need opening individually work out to about 26 investigator-hours back on this batch alone — and we say plainly that the 15-minutes-per-alert figure is our estimate, not a sourced number, because it is.

**Q: How would this integrate with what the bank already runs?**
The same graph-plus-agent pattern is the reusable part, not the synthetic data. Feed clustering from a real transaction-monitoring feed instead of ours, route an approved narrative into the SAR filing workflow, and the precedent knowledge base doubles as onboarding material for new investigators. The pattern also applies directly to fraud and sanctions screening — anywhere alerts need triage instead of individual scoring.

**Q: Does this only work for AML?**
The typology detection (structuring, round-tripping, mule-hub) is AML-specific, but the underlying pattern — cluster first, argue both sides, cite everything, human signs off — is domain-agnostic. Fraud and sanctions screening are the two most direct next targets.

**Q: What's the realistic path to production — or is this just a hackathon toy?**
We laid out an explicit, phased timeline rather than a hand-wave: discovery and validation, real data integration, model validation and red-teaming, security hardening, a shadow-mode pilot that runs alongside the existing manual process with zero automated actions, then phased rollout — roughly 6–9 months to a cautious first pilot. That's slower than a feature launch on purpose, because this touches AML compliance decisions, and we'd rather present a credible timeline than an unrealistic one.

---

## The hard questions (a sharp technical judge will ask at least one of these)

**Q: Isn't clustering by shared accounts just a database join? Why call that innovation?**
The join is simple; recognizing it's the right *first* step before spending LLM calls is the actual insight. Nobody's claiming graph analytics is new technology — the innovation is architectural: refusing to let the "obvious" approach (LLM scores every alert) be the whole solution, and using cheap deterministic computation to make the expensive reasoning worth its cost.

**Q: Where does the Enterprise Gateway / OAuth piece actually stand — is it built, or just a diagram?**
Honestly: it's a real interface implementation in the codebase, behind the same `LLMClient` abstraction as every other provider, but its connection to an actual bank-hosted gateway is a stub — there's no real gateway to connect to yet, because we don't control that infrastructure. What's running live in this demo is the Cached Replay path, fixtures recorded from real model calls during our own development. That's the honest state, and it's exactly why the architecture is provider-agnostic in the first place: swapping in a real gateway later is a config change, not a rewrite.

**Q: Could a bad actor game the Defense agent into always finding an excuse?**
Not without it showing up as a specific, checkable citation that doesn't hold up — the Defense agent's claims go through the same citation validation as the Prosecutor's. If the "innocent explanation" doesn't survive scrutiny against real case data, the Adjudicator isn't obligated to accept it, and a human reviews the full reasoning either way.

**Q: Your dataset is synthetic. How do you know this works on real, messy bank data?**
We don't yet, and we say so — that's precisely what the model-validation and shadow-mode-pilot phases in the roadmap are for, run against real historical cases before anything touches a live decision. The synthetic dataset is modeled on real UCP4.0 field categories specifically so the transition isn't a redesign, but validation against real data is a proposed next step, not a result we're claiming today.

**Q: What stops someone from bypassing the UI and hitting the API directly to dodge RBAC?**
Nothing about the frontend matters for that — role enforcement happens server-side on every request via `_require_role()`, regardless of what UI (or lack of one) is making the call. The persona picker is a demo convenience; the actual boundary is in the API layer.

**Q: Did you use AI tools to help build this yourselves?**
Yes — GitHub Copilot on the locked-down laptop, Claude for architecture and implementation throughout. We think that's a legitimate answer, not a confession: using AI well across the SDLC, not just inside the product, is consistent with the pitch, not in tension with it.

**Q: What's the hardest technical problem you actually hit?**
Structured LLM output isn't 100% reliable — the model would occasionally omit a required field, always the last field in the schema, always after a long free-text field. We fixed it by reordering schemas to put structured fields first, raising the token budget, and adding required-field validation with a retry loop that never caches a malformed response. It reduced the failure rate substantially but we don't claim it's eliminated — that's an honest limitation, not a solved problem.

**Q: What's the actual risk of implementing this in real life, and how would you deal with it?**
Four categories worth naming honestly rather than glossing over:
- **Regulatory risk** — AML tooling sits inside model risk management requirements (OSFI-style guidance for a Canadian bank). We treat that as a design input, not an afterthought: nothing auto-executes, every decision gets a human sign-off, and the audit trail is tamper-evident from day one — exactly the evidence a model risk review would want. The roadmap's validation and shadow-mode-pilot phases exist specifically to build that evidence *before* anything touches a live decision.
- **False negatives** — the system only recognizes the typologies we've built playbooks for (structuring, round-tripping, mule-hub); a scheme outside that scope wouldn't be caught, and "the AI didn't flag it" could create false confidence. That's exactly why this is positioned as a triage layer on top of existing transaction monitoring, not a replacement for it, and why expanding typology coverage is an explicit next step, not something we're claiming is complete.
- **Bias risk** — AML systems have a real history of disparate impact. Demographic and segmentation fields are shown to investigators for context but structurally excluded from automated scoring — only financial-capacity signals feed behavioral detection. But we haven't run a full fairness audit against protected classes; that's part of the model-validation phase, not a result we have today.
- **Automation complacency** — the risk that a human reviewer starts rubber-stamping AI verdicts over time instead of actually scrutinizing them, which quietly defeats the human-in-the-loop safeguard on paper. The UI is built to make that a little harder — investigators see both arguments and their citations, not just a final score — but that's ultimately a process risk a bank would need to actively monitor, like periodic audit sampling of approved cases, not something a UI choice alone solves.
