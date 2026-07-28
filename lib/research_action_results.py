from __future__ import annotations

from typing import Any


def build_action_result_card(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": result.get("title") or result.get("action") or "Research action",
        "status": "ok" if result.get("ok") else "error",
        "message": result.get("message", ""),
        "object_type": result.get("object_type", ""),
        "object_id": result.get("object_id", ""),
        "source": result.get("source", "manual"),
        "caveat": result.get("caveat", "Manual research workflow; source caveats remain visible."),
        "research_only": True,
    }


def build_action_error_card(action: str, error: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "title": "Action not run",
        "status": "error",
        "action": action,
        "error": error,
        "details": details or {},
        "caveat": "No workspace mutation was performed.",
        "research_only": True,
    }
