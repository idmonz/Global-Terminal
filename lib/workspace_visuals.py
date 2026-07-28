from __future__ import annotations

from typing import Any

from .workspace_summary_engine import RESEARCH_ONLY_NOTICE


def build_workspace_metric_cards(summary: dict[str, Any]) -> list[dict[str, Any]]:
    counts = summary.get("counts", {})
    return [
        {"label": "Tracked Items", "value": counts.get("watchlist_items", 0), "status": "local"},
        {"label": "Active Alert Rules", "value": counts.get("active_alert_rules", 0), "status": "manual"},
        {"label": "Open Reports", "value": counts.get("reports", 0), "status": "local"},
        {"label": "Strategy Records", "value": counts.get("strategy_commits", 0), "status": "research"},
    ]


def build_workspace_quick_action_cards() -> list[dict[str, Any]]:
    return [
        {"title": "Add watchlist item", "command": "ADD WATCHLIST", "page": "pages/20_Watchlist_Alerts.py", "status": "available"},
        {"title": "Evaluate alerts now", "command": "EVALUATE ALERTS", "page": "pages/20_Watchlist_Alerts.py", "status": "manual"},
        {"title": "Generate Watchlist Brief", "command": "GENERATE WATCHLIST BRIEF", "page": "pages/21_Report_Inbox.py", "status": "manual"},
        {"title": "Generate Provider Health Report", "command": "GENERATE PROVIDER REPORT", "page": "pages/21_Report_Inbox.py", "status": "manual"},
        {"title": "Create Strategy Commit", "command": "COMMIT STRATEGY", "page": "pages/22_Strategy_Decision_Log.py", "status": "manual"},
        {"title": "Open War Room", "command": "GLOBAL WAR", "page": "pages/14_War_Room.py", "status": "navigation"},
        {"title": "Open Energy Geopolitics", "command": "CL ENERGY", "page": "pages/9_Energy_Geopolitics.py", "status": "navigation"},
        {"title": "Open Data Provider Center", "command": "DATA PROBE", "page": "pages/17_Data_Provider_Center.py", "status": "navigation"},
    ]


def build_research_only_notice() -> str:
    return RESEARCH_ONLY_NOTICE

