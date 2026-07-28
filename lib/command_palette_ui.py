from __future__ import annotations

from typing import Any

from .command_palette_suggestions import build_quick_add_payload, search_research_objects, suggest_actions_for_query
from .research_command_safety import build_blocked_research_boundary_card, detect_forbidden_command_intent
from .research_object_resolver import resolve_research_object
from .source_freshness_strip import build_source_freshness_strip


def build_command_result_card(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": action.get("label", "Command result"),
        "command": action.get("command", ""),
        "page": action.get("page", ""),
        "object": action.get("object", ""),
        "enabled": bool(action.get("enabled", True)),
        "reason": action.get("reason", ""),
        "safe_alternatives": action.get("safe_alternatives", []),
        "data_required": action.get("data_required", "manual research context"),
        "output_type": action.get("output_type", "research workflow"),
        "caveat": action.get("caveat", action.get("reason", "Research-only workflow.")),
        "research_only": True,
    }


def build_command_palette_state(query: str = "", *, source_snapshot: Any = None) -> dict[str, Any]:
    safety = detect_forbidden_command_intent(query)
    obj = resolve_research_object(query if not safety.get("blocked") else safety.get("safe_query", ""))
    actions = suggest_actions_for_query(query)
    blocked_card = build_blocked_research_boundary_card(query) if safety.get("blocked") else None
    return {
        "query": query,
        "resolved_object": obj,
        "safety": safety,
        "blocked_card": blocked_card,
        "suggestions": actions,
        "quick_add": build_quick_add_payload(query) if query and actions and actions[0].get("enabled", True) else {},
        "result_cards": [build_command_result_card(action) for action in actions],
        "source_freshness": build_source_freshness_strip(source_snapshot, title="Command context freshness"),
        "placeholder": "Search ticker, crypto pair, provider, region, strategy, or report topic...",
        "research_only": True,
    }


__all__ = [
    "build_command_palette_state",
    "search_research_objects",
    "suggest_actions_for_query",
    "build_quick_add_payload",
    "build_command_result_card",
    "resolve_research_object",
]

from pathlib import Path
from .research_workflow_actions import run_research_workflow_action


def run_command_palette_action(action: dict[str, Any], *, query: str = "", db_path: str | Path | None = None) -> dict[str, Any]:
    """Run a safe command-palette action through the workflow layer."""
    if not action.get("enabled", True) or action.get("command") == "BLOCKED_RESEARCH_BOUNDARY":
        return {"ok": False, "status": "blocked", "blocked_card": build_blocked_research_boundary_card(query), "research_only": True}
    command = str(action.get("command", "")).upper()
    if command == "ADD WATCHLIST":
        return run_research_workflow_action("ADD_WATCHLIST_ITEM", {"query": query or action.get("object", "")}, db_path=db_path)
    if command in {"GENERATE WATCHLIST BRIEF", "GENERATE ASSET BRIEF", "GENERATE CRYPTO WATCH"}:
        return run_research_workflow_action("GENERATE_WATCHLIST_BRIEF", {"title": f"{query or action.get('object', 'Manual')} research brief"}, db_path=db_path)
    if command == "GENERATE PROVIDER REPORT":
        return run_research_workflow_action("GENERATE_PROVIDER_REPORT", {"title": f"{query or action.get('object', 'Provider')} health report"}, db_path=db_path)
    if command == "GENERATE WAR ROOM BRIEF":
        return run_research_workflow_action("GENERATE_WAR_ROOM_BRIEF", {"region": query or action.get("object", "")}, db_path=db_path)
    if command == "GENERATE ENERGY BRIEF":
        return run_research_workflow_action("GENERATE_ENERGY_BRIEF", {"region": query or action.get("object", "")}, db_path=db_path)
    if command == "GENERATE STRATEGY REVIEW":
        return run_research_workflow_action("GENERATE_STRATEGY_REVIEW", {"title": f"{query or action.get('object', 'Strategy')} review"}, db_path=db_path)
    if command == "COMMIT STRATEGY":
        return run_research_workflow_action("CREATE_STRATEGY_COMMIT", {"strategy_id": query or "manual_strategy_candidate", "message": "Created from command palette workflow."}, db_path=db_path)
    return {"ok": True, "status": "route_only", "page": action.get("page", ""), "message": "Open the target page to continue the manual research workflow.", "research_only": True}

__all__.append("run_command_palette_action")
