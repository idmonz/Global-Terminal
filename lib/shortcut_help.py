from __future__ import annotations

from typing import Any

from .shortcut_registry import build_shortcut_registry


def build_shortcut_help_rows() -> list[dict[str, Any]]:
    return [
        {
            "shortcut": item["shortcut"],
            "command": item["command"],
            "label": item["label"],
            "workspace": item["workspace"],
            "description": item["description"],
            "page": item["page"],
        }
        for item in build_shortcut_registry()
    ]


def search_shortcuts(query: str) -> list[dict[str, Any]]:
    needle = str(query or "").lower()
    rows = build_shortcut_help_rows()
    if not needle:
        return rows
    return [row for row in rows if any(needle in str(value).lower() for value in row.values())]


def build_shortcut_help_panel(query: str = "") -> dict[str, Any]:
    rows = search_shortcuts(query)
    return {
        "title": "Command Help",
        "summary": "Shortcuts open research workspaces and diagnostics. They do not execute trades.",
        "rows": rows,
        "count": len(rows),
        "caveat": "Command UX is navigation and research-only.",
    }
