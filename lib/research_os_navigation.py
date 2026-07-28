from __future__ import annotations
from pathlib import Path
from typing import Any
from .workspace_store import get_workspace_counts

GOAL11B_PAGES = [
    {"label": "Research Workspace", "page": "pages/19_Research_Workspace.py", "command": "WORKSPACE", "purpose": "Daily research command center."},
    {"label": "Watchlist & Alerts", "page": "pages/20_Watchlist_Alerts.py", "command": "WATCHLIST", "purpose": "Tracked assets, regions, providers, strategies, and alert state."},
    {"label": "Report Inbox", "page": "pages/21_Report_Inbox.py", "command": "REPORTS", "purpose": "Manual research reports with source snapshots."},
    {"label": "Strategy Decision Log", "page": "pages/22_Strategy_Decision_Log.py", "command": "STRATEGY LOG", "purpose": "Research commit records, guard results, and forward tracking."},
    {"label": "Research Tool Center", "page": "pages/23_Research_Tool_Center.py", "command": "TOOL CENTER", "purpose": "Catalog of manual research tools and diagnostics."},
]


def build_research_os_nav_cards(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    counts = get_workspace_counts(db_path)
    count_map = {"WORKSPACE": counts.get("watchlist_items", 0), "WATCHLIST": counts.get("active_alert_rules", 0), "REPORTS": counts.get("reports", 0), "STRATEGY LOG": counts.get("strategy_commits", 0), "TOOL CENTER": 0}
    return [{**row, "count": count_map.get(row["command"], 0), "research_only": True} for row in GOAL11B_PAGES]


def build_research_os_status_card(db_path: str | Path | None = None) -> dict[str, Any]:
    counts = get_workspace_counts(db_path)
    return {"title": "Personal Research OS", "summary": f"Watchlist {counts['watchlist_items']} | alerts {counts['active_alert_rules']} | reports {counts['reports']} | strategy commits {counts['strategy_commits']}", "commands": [p["command"] for p in GOAL11B_PAGES], "pages": [p["page"] for p in GOAL11B_PAGES], "research_only": True}
