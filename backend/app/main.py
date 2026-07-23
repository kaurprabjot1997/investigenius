from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Explicit path rather than load_dotenv()'s CWD-based search, so this works
# regardless of where uvicorn is launched from. Must run before any request
# reaches app.llm.client (which reads LLM_PROVIDER/ANTHROPIC_API_KEY from
# os.environ) — module import time, here, is early enough.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.api.routes import router  # noqa: E402

app = FastAPI(title="InvestiGenius API")

# Local dev only (Vite default port). Tighten or remove before anything
# beyond a laptop demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
