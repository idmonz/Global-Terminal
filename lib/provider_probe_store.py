from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROBE_PATH = ROOT_DIR / "data" / "private" / "provider_probe_results.json"


def get_provider_probe_store_path(path: str | Path | None = None) -> Path:
    return Path(path) if path else DEFAULT_PROBE_PATH


def save_provider_probe_results(results: list[dict[str, Any]], path: str | Path | None = None) -> Path:
    target = get_provider_probe_store_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"saved_at": datetime.now(timezone.utc).isoformat(), "results": results}
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def load_provider_probe_results(path: str | Path | None = None) -> dict[str, Any]:
    target = get_provider_probe_store_path(path)
    if not target.exists():
        return {"saved_at": None, "results": []}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        data.setdefault("results", [])
        return data
    except Exception as exc:
        return {"saved_at": None, "results": [], "error": str(exc)}


def provider_probe_store_is_gitignored() -> bool:
    gitignore = ROOT_DIR / ".gitignore"
    if not gitignore.exists():
        return False
    text = gitignore.read_text(encoding="utf-8", errors="ignore")
    return "data/private/" in text or "provider_probe_results.json" in text
