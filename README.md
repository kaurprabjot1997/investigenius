# InvestiGenius — setup

AI investigation copilot for AML alert triage. This file is "how to get it running" — for the full feature writeup and pitch narrative, see `static_ui/TEAM_BRIEFING.md`.

## What's included

- **Sign-in** (persona picker) → **Case Queue** (sortable/filterable, click "See how ▾" on any row for an "alerts → AI clustering → network" preview) and **Alerts Queue** (the raw alert inbox before clustering — every alert, its type, and which case it was automatically merged into)
- **Case Detail**: interactive network graph (hover to trace connections, click a node for its profile, particle animation shows fund flow), client profile panel, automated behavioral signals, investigation playbook
- **AI Investigation**: Prosecutor/Defense/Adjudicator pipeline, structured output only, deterministic citation validation, confidence gating — a human always makes the final call
- **Precedent Chat**: searches *other* cases' recorded findings and decisions (never the current case's own evidence) — the institutional-memory half of the product; a feedback loop writes to this knowledge base every time a case is investigated or approved/rejected
- Hash-chained audit log, RBAC enforced server-side (role comes from whichever persona signed in, not a separate switcher)
- **Works fully offline** via cached fixtures — no live LLM access required to demo. Fixtures for all 4 featured cases (`case_001`, `case_005`, `case_007`, `case_013`) — both investigation *and* precedent chat — already ship in this repo.

## Personal laptop (development, real API access)

```
cd backend
py -3.12 -m venv .venv        # use `py`, not `python` — see note below
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # macOS/Linux: cp .env.example .env
```

> On Windows, the bare `python` command can resolve to a Store install-stub instead of a real interpreter even when Python is properly installed — a PATH-ordering quirk (Store "app execution aliases" for `python.exe` take precedence). Use `py -3.12` for the initial venv creation; once activated, the venv's own `python`/`pip` resolve correctly since activation puts `.venv\Scripts` first on PATH. To remove the stub permanently: Settings → Apps → Advanced app settings → App execution aliases → turn off the `python.exe`/`python3.exe` entries.

Edit `.env`: set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=<your key>` if you want to record new fixtures or use live chat/investigation. Otherwise leave `LLM_PROVIDER=cache` (default) — the 4 featured cases already work offline.

**Populate the database — required on every fresh clone, not optional.** `backend/investigenius.db` is gitignored (it's generated data, not source), so it does not come with the repo. Without this step the app runs fine but the Case Queue and Alerts Queue are empty:
```
python -m data.generate_dataset
python -m app.graph.clustering
```
The first command seeds synthetic accounts/transactions/alerts (fixed random seed — same data every time, including the exact `case_001`/`005`/`007`/`013` structure the shipped fixtures were recorded against). The second clusters them into risk-scored cases. Re-run both any time you want a fresh dataset (this wipes and regenerates case/knowledge data, never the audit log).

```
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:
```
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** (use `localhost`, not `127.0.0.1` — Vite binds IPv6 by default). Sign in as any persona, and `case_001`/`005`/`007`/`013` already have full investigation + precedent chat available with zero setup.

### Recording fixtures for additional cases (optional)

Only needed if you want live-API-recorded demo cases beyond the 4 already shipped. With `LLM_PROVIDER=anthropic` set:
```
python ..\scripts\record_fixtures.py case_XXX          # investigation fixtures + knowledge base entry
```
Then, in the running app, click Approve/Reject on that case a couple of times (varied — include at least one reject) so the precedent-chat knowledge base has real decision data to draw on. Only then:
```
python ..\scripts\record_chat_fixtures.py case_XXX      # precedent chat fixtures
```
This order matters — recording chat fixtures before there's decision data just bakes in "no precedent found" answers. Both scripts refuse to run unless `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` are set (protects against silently hitting the cache client instead of the real API). Set `LLM_PROVIDER` back to `cache` when done.

## Bank laptop (demo day)

```
git clone https://github.com/kaurprabjot1997/investigenius.git
```
Then the same steps as above — **including `python -m data.generate_dataset` and `python -m app.graph.clustering`; the database is never in the repo, so this step is required here too, every time.** In `.env` leave `LLM_PROVIDER=cache` (the default — do not set `ANTHROPIC_API_KEY` here). The app then runs entirely off the fixtures already in the repo — zero network calls to any LLM, and all 4 featured cases work out of the box. If bank IT confirms gateway access before the hackathon, set `LLM_PROVIDER=gateway` and fill in `GATEWAY_*` in `.env` instead; no code changes needed either way.

If `pip install` fails immediately on the bank laptop, it's almost always a corporate proxy/mirror issue, not a package problem — check with IT for the internal index URL before assuming something's broken.

**If GitHub isn't reachable from the bank network**, fall back to a zip transfer from the personal laptop:
```
git archive HEAD -o investigenius.zip
```
`git archive` respects `.gitignore`, so `.venv/`, `node_modules/`, `.env`, and the SQLite db are never included — only source, lockfiles, and the recorded fixtures. Before zipping, run `pip-audit` (backend) and `npm audit` (frontend) to confirm no known CVEs in the pinned versions.
