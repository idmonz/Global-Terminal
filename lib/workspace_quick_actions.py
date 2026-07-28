from __future__ import annotations
from pathlib import Path
from typing import Any
from .watchlist_models import infer_item_type
from .watchlist_store import create_watchlist_item
from .alert_evaluator import evaluate_all_alerts
from .headless_report_runner import run_report_generator
from .strategy_decision_log import create_strategy_commit


def build_quick_actions() -> list[dict[str, Any]]:
    return [
        {"code": "ADD WATCHLIST", "label": "Add watchlist item", "manual": True},
        {"code": "EVALUATE ALERTS", "label": "Evaluate alerts now", "manual": True},
        {"code": "GENERATE WATCHLIST BRIEF", "label": "Generate Watchlist Brief", "manual": True},
        {"code": "COMMIT STRATEGY", "label": "Create Strategy Commit", "manual": True},
    ]


def run_quick_action(action: str, payload: dict[str, Any] | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
    payload = payload or {}; code = str(action or "").upper()
    if code == "ADD WATCHLIST":
        value = payload.get("symbol") or payload.get("display_name") or "Research Item"
        return {"action": code, "result": create_watchlist_item(item_type=payload.get("item_type") or infer_item_type(value), symbol=payload.get("symbol", value), display_name=payload.get("display_name", value), tags=payload.get("tags", []), db_path=db_path)}
    if code == "EVALUATE ALERTS":
        return {"action": code, "result": evaluate_all_alerts(payload.get("data_context", {}), db_path=db_path)}
    if code.startswith("GENERATE"):
        name = "watchlist" if "WATCHLIST" in code else "provider" if "PROVIDER" in code else "war_room" if "WAR ROOM" in code else "strategy" if "STRATEGY" in code else "daily"
        return {"action": code, "result": run_report_generator(name, db_path=db_path)}
    if code == "COMMIT STRATEGY":
        return {"action": code, "result": create_strategy_commit(strategy_id=payload.get("strategy_id", "manual_strategy"), message=payload.get("message", "Manual research commit"), db_path=db_path)}
    return {"action": code, "error": "Unknown quick action", "research_only": True}

