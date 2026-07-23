"""Fixture storage for CachedReplayClient. One JSON file per cache_key under
cache/fixtures/ — inspectable, diffable, and safe to ship inside the transfer
zip (it's synthetic demo data, not real customer records).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "cache" / "fixtures"
_SAFE_KEY = re.compile(r"[^a-zA-Z0-9_.-]")


def _fixture_path(cache_key: str) -> Path:
    # cache_key is derived from case IDs we control (not raw user input), but
    # sanitize anyway so a malformed key can't write outside the fixture dir.
    safe_name = _SAFE_KEY.sub("_", cache_key)
    return _FIXTURE_DIR / f"{safe_name}.json"


def load_fixture(cache_key: str) -> dict[str, Any] | None:
    path = _fixture_path(cache_key)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_fixture(cache_key: str, response: dict[str, Any]) -> None:
    _FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = _fixture_path(cache_key)
    path.write_text(json.dumps(response, indent=2), encoding="utf-8")


def list_recorded_cache_keys() -> list[str]:
    if not _FIXTURE_DIR.exists():
        return []
    return sorted(p.stem for p in _FIXTURE_DIR.glob("*.json"))
