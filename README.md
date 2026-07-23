# InvestiGenius — setup

## Personal laptop (development, real API access)

```
cd backend
py -3.12 -m venv .venv        # use `py`, not `python` — see note below
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # macOS/Linux: cp .env.example .env
```

> On this machine, the bare `python` command resolves to a Windows Store install-stub, not a real interpreter, even with Python 3.12 properly installed — a PATH-ordering quirk (Store "app execution aliases" for `python.exe` take precedence). Use `py -3.12` for the initial venv creation; once activated, the venv's own `python`/`pip` resolve correctly since activation puts `.venv\Scripts` first on PATH. To remove the stub permanently: Settings → Apps → Advanced app settings → App execution aliases → turn off the `python.exe`/`python3.exe` entries.
Edit `.env`: set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=<your key>`.

```
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. Click "Run investigation" — this calls the real API and automatically writes/updates fixture files under `backend/cache/fixtures/`. Repeat for every demo case you plan to show, so every one is recorded before you leave this laptop.

## Bank laptop (demo day)

Same steps, except in `.env` leave `LLM_PROVIDER=cache` (the default — do not set `ANTHROPIC_API_KEY` here). The app then runs entirely off the fixtures recorded above — zero network calls to any LLM. If bank IT confirms gateway access before the hackathon, set `LLM_PROVIDER=gateway` and fill in `GATEWAY_*` in `.env` instead; no code changes needed either way.

If `pip install` fails immediately on the bank laptop, it's almost always a corporate proxy/mirror issue, not a package problem — check with IT for the internal index URL before assuming something's broken.

## Packaging for transfer

From the personal laptop, after recording fixtures for all demo cases:
```
git init                      # first time only
git add .
git commit -m "InvestiGenius starter"
git archive HEAD -o investigenius.zip
```
`git archive` respects `.gitignore`, so `.venv/`, `node_modules/`, `.env`, and the SQLite db are never included — only source, lockfiles, and the recorded fixtures.

Before zipping, run `pip-audit` (backend) and `npm audit` (frontend) to confirm no known CVEs in the pinned versions.
