from __future__ import annotations

from typing import Any


def build_empty_state_panel(
    title: str,
    *,
    message: str = "No supplied context is available yet.",
    next_actions: list[dict[str, Any]] | None = None,
    caveat: str = "No placeholder data is fabricated.",
) -> dict[str, Any]:
    return {
        "title": title,
        "message": message,
        "next_actions": next_actions or [],
        "caveat": caveat,
        "state": "empty",
        "research_only": True,
    }
