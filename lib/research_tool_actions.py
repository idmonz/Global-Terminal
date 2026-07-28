from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_tool_center import build_research_tool_center_payload
from .research_workflow_actions import run_research_workflow_action

_TOOL_ACTION_MAP = {
    "Evaluate Alerts Now": "EVALUATE_ALERTS_NOW",
    "Generate Watchlist Brief": "GENERATE_WATCHLIST_BRIEF",
    "Generate Provider Health Report": "GENERATE_PROVIDER_REPORT",
    "Generate War Room Brief": "GENERATE_WAR_ROOM_BRIEF",
    "Generate Strategy Review": "GENERATE_STRATEGY_REVIEW",
    "Create Strategy Commit": "CREATE_STRATEGY_COMMIT",
    "Export Workspace JSON": "EXPORT_WORKSPACE_JSON",
    "Backup Workspace DB": "BACKUP_WORKSPACE_DB",
    "Run Provider Probe": "RUN_PROVIDER_PROBE_DRY_RUN",
    "Inspect Data Quality": "INSPECT_DATA_QUALITY",
    "Build War Room Brief": "BUILD_WAR_ROOM_CONTEXT",
    "Inspect View Presets": "INSPECT_VIEW_PRESETS",
    "Inspect Release Hygiene": "INSPECT_RELEASE_HYGIENE",
    "Price Option": "PRICE_OPTION",
    "Solve Implied Volatility": "SOLVE_IV",
    "Build Payoff Scenario": "PAYOFF_SCENARIO",
    "Generate Options Report": "OPTIONS_REPORT",
    "Attach Options Result to Strategy Commit": "ATTACH_OPTIONS_RESULT_TO_STRATEGY_COMMIT",
    "Create Quant Model Snapshot": "CREATE_QUANT_MODEL_SNAPSHOT",
    "Attach Model Snapshot to Report": "ATTACH_MODEL_SNAPSHOT_TO_REPORT",
    "Inspect Options Provider Capability": "INSPECT_OPTIONS_PROVIDER_CAPABILITY",
    "Import Option Chain CSV": "IMPORT_OPTION_CHAIN_CSV",
}


def _all_tools() -> list[dict[str, Any]]:
    payload = build_research_tool_center_payload()
    tools: list[dict[str, Any]] = []
    for section in payload.get("sections", []):
        for tool in section.get("tools", []):
            tools.append({**tool, "section": section.get("section", "")})
    return tools


def search_research_tools(query: str = "") -> list[dict[str, Any]]:
    rows = _all_tools()
    needle = str(query or "").lower()
    if not needle:
        return rows
    return [tool for tool in rows if needle in " ".join(str(v).lower() for v in tool.values())]


def get_research_tool_definition(tool_name: str) -> dict[str, Any] | None:
    normalized = str(tool_name or "").lower()
    for tool in _all_tools():
        if tool.get("tool_name", "").lower() == normalized or tool.get("command", "").lower() == normalized:
            action = tool.get("workflow_action") or _TOOL_ACTION_MAP.get(tool.get("tool_name"))
            disabled_reason = tool.get("route_only_reason", "") if not action else ""
            return {**tool, "workflow_action": action, "action_enabled": bool(action), "route_only_reason": disabled_reason, "research_only": True}
    return None


def build_tool_missing_data_caveat(tool: dict[str, Any] | None, supplied_data: dict[str, Any] | None = None) -> dict[str, Any]:
    data_required = (tool or {}).get("data_required", "")
    missing = bool(data_required and data_required != "none" and not supplied_data)
    return {
        "missing_data": missing,
        "data_required": data_required,
        "message": "Required context is not supplied; output will be a caveated manual workflow payload." if missing else "Required context is available or optional.",
        "research_only": True,
    }


def build_research_tool_action_result(tool: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_name": tool.get("tool_name", ""),
        "workflow_action": tool.get("workflow_action", ""),
        "status": "ok" if result.get("ok") else "error",
        "result": result,
        "caveat": tool.get("caveat", "Research-only workflow."),
        "research_only": True,
    }


def run_research_tool_action(tool_name: str, payload: dict[str, Any] | None = None, *, db_path: str | Path | None = None) -> dict[str, Any]:
    tool = get_research_tool_definition(tool_name)
    if not tool:
        return {"ok": False, "error": "tool_not_found", "research_only": True}
    if not tool.get("workflow_action"):
        return {"ok": False, "error": "tool_has_no_safe_action", "tool": tool, "research_only": True}
    result = run_research_workflow_action(tool["workflow_action"], payload or {}, db_path=db_path)
    return build_research_tool_action_result(tool, result)
