from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .terminal_function_registry import get_function_definition, search_functions, validate_command_code
from .research_command_palette import route_research_command
from .research_command_safety import build_blocked_research_boundary_card, detect_forbidden_command_intent


FUNCTION_PAGE_MAP = {
    "FA": "pages/15_Financial_Terminal.py",
    "KEY": "pages/15_Financial_Terminal.py",
    "FIL": "pages/15_Financial_Terminal.py",
    "OMON": "pages/15_Financial_Terminal.py",
    "PORT": "pages/16_Portfolio_Quant_Lab.py",
    "CRYPTO": "pages/8_Crypto_Intelligence.py",
    "ENERGY": "pages/9_Energy_Geopolitics.py",
    "WATCH": "pages/20_Watchlist_Alerts.py",
}


@dataclass(frozen=True)
class ParsedCommand:
    raw: str
    normalized: str
    command_type: str
    symbol: str | None = None
    function: str | None = None
    blocked: bool = False


def parse_terminal_command(command: str) -> dict[str, Any]:
    normalized = " ".join(str(command or "").upper().split())
    words = normalized.split()
    blocked = bool(detect_forbidden_command_intent(command).get("blocked"))
    if not normalized:
        parsed = ParsedCommand(command, normalized, "empty")
    elif blocked:
        parsed = ParsedCommand(command, normalized, "blocked", blocked=True)
    elif len(words) == 2 and validate_command_code(normalized) and words[1] in FUNCTION_PAGE_MAP:
        parsed = ParsedCommand(command, normalized, "symbol_function", symbol=words[0], function=words[1])
    elif get_function_definition(normalized):
        parsed = ParsedCommand(command, normalized, "registry")
    else:
        parsed = ParsedCommand(command, normalized, "partial")
    return parsed.__dict__


def build_command_result(parsed: dict[str, Any], definition: dict[str, Any] | None = None) -> dict[str, Any]:
    definition = definition or {}
    return {
        "ok": True,
        "status": "routed",
        "command": parsed["normalized"],
        "symbol": parsed.get("symbol"),
        "function": parsed.get("function") or definition.get("code"),
        "label": definition.get("label") or parsed.get("function") or parsed["normalized"],
        "page": definition.get("page") or FUNCTION_PAGE_MAP.get(str(parsed.get("function") or ""), "app.py"),
        "message": "Open the linked workspace and inspect the source-labeled panels.",
        "research_only": True,
    }


def build_command_error(command: str, reason: str) -> dict[str, Any]:
    if reason == "blocked_action":
        boundary = build_blocked_research_boundary_card(command)
        return {
            "ok": False,
            "status": "blocked",
            "command": " ".join(str(command or "").upper().split()),
            "error": boundary["message"],
            "blocked_card": boundary,
            "suggestions": boundary["safe_alternatives"],
            "research_only": True,
        }
    return {
        "ok": False,
        "status": "not_found",
        "command": " ".join(str(command or "").upper().split()),
        "error": "No matching terminal function.",
        "suggestions": build_command_suggestions(command),
        "research_only": True,
    }


def build_command_suggestions(command: str, limit: int = 5) -> list[dict[str, Any]]:
    normalized = " ".join(str(command or "").upper().split())
    suggestions = search_functions(normalized)[:limit]
    if suggestions:
        return suggestions
    first = normalized.split()[0] if normalized else ""
    if first:
        return search_functions(first)[:limit]
    return search_functions("")[:limit]


def route_terminal_command(command: str) -> dict[str, Any]:
    parsed = parse_terminal_command(command)
    if parsed["command_type"] == "empty":
        return build_command_error(command, "empty")
    if parsed["blocked"]:
        return build_command_error(command, "blocked_action")
    research_route = route_research_command(command)
    if research_route.get("ok"):
        return {**research_route, "message": "Open the linked research workspace. Commands create or route research objects only."}
    definition = get_function_definition(parsed["normalized"])
    if definition:
        return build_command_result(parsed, definition)
    if parsed["command_type"] == "symbol_function":
        return build_command_result(parsed)
    return build_command_error(command, "not_found")
