# InvestiGenius — 7-Minute Demo Script

Timed against the actual judging rubric so time spent maps to points available. Each section names the exact slide in `PITCH_DECK.html` (open it in a browser — arrow keys / space / click the edges to advance, click the dots to jump) and is tagged with the criteria it's earning marks against. Total: 7:00. Practice against a timer — this is tight.

**Core message to land, repeated in different words at open and close:** *we didn't put a chatbot in front of an alert queue — we built a team of agentic AI investigators that work the way real investigators do, with guardrails a bank would actually accept.*

**Real numbers to have memorized:** 205 alerts → 102 network cases (50% reduction), 12 high-risk cases surfaced automatically, 23 distinct alert types in the queue.

**Two presenters works well:** one drives the deck/narration, one drives the live app — cuts every handoff stumble out of the tightest 7 minutes you'll ever run.

---

## 0:00–0:15 — Hook *(Creativity & Innovation — 30%)*

**Slide 1 — Title.**

> "Money laundering rarely lives in one suspicious transaction — it lives in a network of them. InvestiGenius is agentic AI that investigates the way a real team does: building a case, arguing it from both sides, and ruling on it, before a human ever has to start from a blank page."

## 0:15–0:40 — The problem, made specific *(Creativity — 30%)*

**Slide 2 — The Problem.**

> "Real laundering schemes — structuring, round-tripping, mule networks — are network phenomena. They only become visible when you connect multiple accounts. An alert-by-alert scorer, AI or not, structurally cannot see that — it's reading one page of a story that spans twelve."

## 0:40–1:10 — Our wedge, with the numbers *(Creativity — 30%)*

**Slide 3 — Our Wedge.**

> "So before any model runs, we cluster. 205 raw alerts collapse into 102 network cases automatically — a 50% reduction before an investigator or an LLM spends a single second on them. 12 come back high-risk. That's not GenAI — that's graph analytics doing the job GenAI gets asked to do badly, so the expensive reasoning only gets spent where it's earned."

## 1:10–1:55 — Architecture in one breath *(Solution Design — 25%, GenAI Leverage — 20%)*

**Slide 4 — Architecture: Four Agents.**

> "Here's the pipeline. Clustering hands off to the agentic layer: Prosecutor builds the case for suspicion, Defense actively argues the innocent explanation, in parallel — Adjudicator weighs both and rules. Every claim tied to a citation from real case data, or it doesn't count. A fourth agent, Precedent Chat, lets an investigator ask 'have we seen this before' against every other case's recorded findings."

**Why this section matters:** names all four agents once, cleanly, before the live demo shows them — judges should recognize each one when it appears live.

## 1:55–2:00 — Transition

**Slide 5 — "Now, live."** *(five seconds, just say it and switch windows)*

> "Let's look at case_001."

## 2:00–4:30 — LIVE DEMO *(GenAI Leverage 20%, User-Friendly Design 15%, Creativity 30%, Solution Design 25% — the whole rubric lands here)*

**Switch to the live app. This is the largest block of time — it needs to do the most work.**

- Open **Alerts Queue**. *"This is the actual inbox — 205 alerts, 23 different monitoring rules firing. This is 'high volume of alerts' from the brief, made literal, not a slide claim."*
- Switch to **Case Queue**. *"Same alerts — now automatically clustered into 102 network cases. 12 of those are high-risk; the other 90 are single benign transactions the system already knows not to waste investigator time on."*
- Click **"See how ▾"** on the top case. *"This is the literal answer to 'how does the AI build a case from alerts' — alerts on the left, the network they clustered into on the right, live."*
- Open the case. Let the **network graph** sit for a second — hover a node to trace connections, click one for its profile. *"Not a static diagram — investigators can trace it live, and every account here has a mock client profile behind it."*
- Point at **Automated Signals** and the **Investigation Playbook**. *"Before any LLM call, the system already flags behavioral red flags and checks this case against a published, typology-specific criteria list — same checklist, every case, every time. That's standardization, not vibes."*
- Click **Run investigation**. Let the staged reveal play — *"Prosecutor building the case for suspicion… Defense searching for legitimate explanations… Adjudicator weighing both."* Point at the verdict badge, confidence %, and citation tags on each claim.
- Point at the **Source: Live model call / Replayed (cached) response** badge. *"This works with zero live model access, too — everything you're seeing can run fully offline, because we can't guarantee LLM access on a locked-down machine, and we built for that reality instead of hoping around it."*
- Scroll to **Ask About Prior Investigations** (the purple "Institutional memory" panel), click a suggested question. *"This is deliberately not the same thing as the investigation panel above — it never looks at this case's own evidence, it searches every OTHER case's recorded findings and decisions. Every investigation and every human approve or reject — including an override — writes into this knowledge base automatically. The system gets smarter as the team works."*
- Click **Approve**. *"A human always makes the final call — and that action just wrote to a hash-chained audit log."*

## 4:30–5:10 — Guardrails, out loud *(Solution Design — 25%)*

**Slide 6 — Guardrails.** *(back to the deck)*

> "Nothing here auto-executes. Every claim is validated against real case data — if the model can't back it up, it's flagged for mandatory review, not trusted. Every action writes to a hash-chained audit log — tamper-evident by construction, not by policy. That's the difference between a hackathon toy and something a bank could actually imagine deploying."

## 5:10–5:50 — Beyond the demo *(Potential Impact — 10%, Creativity — 30%)*

**Slide 7 — Beyond the Demo.**

> "This isn't a point solution. The same graph-plus-agent pattern plugs into what the bank already runs: feed it from your real transaction monitoring system instead of our synthetic data; route the approved narrative straight into the SAR filing workflow; use the precedent knowledge base to onboard new investigators faster than a binder ever could; the same clustering-plus-adjudication pattern applies directly to fraud and sanctions screening. One architecture, four places it pays for itself."

## 5:50–6:30 — Close *(recap all criteria)*

**Slide 8 — Close.**

> "That's InvestiGenius: agentic AI that argues both sides of a case, cites its evidence, defers to a human for the final call, and keeps working even without a live model connection. Using agentic AI, we're solving a real business problem — not demoing a chatbot."

## 6:30–7:00 — Buffer

Held in reserve — a slow click, a laptop hiccup, or a question that lands mid-flow. If everything ran clean, land here and open the floor early rather than rushing the close.

---

## Pre-demo checklist

- [ ] `LLM_PROVIDER=cache` in `backend/.env` — don't let a live call fail mid-pitch
- [ ] Backend + frontend both running, browser already open to the sign-in screen, tab pinned
- [ ] Pick **case_001** for the live investigation run (it's the fully-recorded, richest fixture)
- [ ] Know which persona to sign in as (Priya Sharma / Senior AML Investigator — can approve, matches the demo flow)
- [ ] `static_ui/PITCH_DECK.html` open in one tab (works offline, no build step — just open the file), the live app in another; know the keyboard shortcut (arrow keys / space) to advance slides without hunting for a mouse click
- [ ] Backup: `static_ui/index.html` open in a third tab in case the live app or wifi fails mid-pitch — it's a static snapshot of the same 4 featured cases, zero server required
- [ ] Rehearse once against a real timer — 7 minutes is tighter than it feels in your head, and the live-demo block (2:00–4:30) is the one most likely to overrun
