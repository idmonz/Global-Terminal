from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


MAX_HISTORY = 50
_HISTORY: list[dict[str, Any]] = []


def add_command_history(command: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": " ".join(str(command or "").upper().split()),
        "status": (result or {}).get("status", "recorded"),
        "page": (result or {}).get("page", ""),
    }
    _HISTORY.append(entry)
    del _HISTORY[:-MAX_HISTORY]
    return entry


def get_command_history(limit: int | None = None) -> list[dict[str, Any]]:
    rows = list(_HISTORY)
    return rows[-limit:] if limit else rows


def clear_command_history() -> None:
    _HISTORY.clear()


def build_command_history_table(limit: int | None = None) -> list[dict[str, Any]]:
    return get_command_history(limit=limit)
