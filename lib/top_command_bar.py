from __future__ import annotations

from typing import Any

from .shortcut_help import build_shortcut_help_panel
from .shortcut_registry import build_shortcut_registry, shortcut_to_command
from .source_freshness_indicator import build_source_freshness_indicator


def build_command_bar_placeholder() -> str:
    return "Search a ticker, page, provider, or command..."


def validate_command_bar_action(action: str) -> dict[str, Any]:
    from .research_command_safety import detect_forbidden_command_intent

    safety = detect_forbidden_command_intent(action)
    blocked = bool(safety.get("blocked"))
    return {
        "ok": not blocked,
        "blocked": blocked,
        "reason": "Research navigation only; trade execution language is blocked." if blocked else None,
        "matched": safety.get("matched", []),
        "safe_query": safety.get("safe_query", ""),
        "research_only": True,
    }


def build_command_suggestions(context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or {}
    suggestions = build_shortcut_registry()
    focus = str(context.get("focus") or "").lower()
    if focus:
        suggestions = [item for item in suggestions if focus in item["workspace"].lower() or focus in item["label"].lower()] or suggestions
    return suggestions[:6]


def build_top_command_bar_state(
    current_command: str = "",
    *,
    route_result: dict[str, Any] | None = None,
    shortcuts: list[dict[str, Any]] | None = None,
    freshness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    command = shortcut_to_command(current_command) or current_command
    validation = validate_command_bar_action(command)
    return {
        "command": command,
        "placeholder": build_command_bar_placeholder(),
        "route_result": route_result or {},
        "shortcuts": shortcuts or build_command_suggestions(),
        "help": build_shortcut_help_panel(),
        "freshness": freshness or build_source_freshness_indicator("terminal session", status="unknown"),
        "validation": validation,
        "research_only": True,
    }
