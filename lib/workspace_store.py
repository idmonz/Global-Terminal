from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_workspace_db import execute_query


def count_table(table: str, where: str = "", params: tuple[Any, ...] = (), db_path: str | Path | None = None) -> int:
    allowed = {
        "watchlist_items", "alert_rules", "alert_events", "report_inbox_items",
        "strategy_commits", "provider_health_snapshots", "data_quality_snapshots", "workspace_activity_log",
    }
    if table not in allowed:
        raise ValueError(f"Unsupported workspace table: {table}")
    query = f"SELECT COUNT(*) AS count FROM {table} {where}"
    row = execute_query(query, params, fetch=True, one=True, db_path=db_path)
    return int((row or {}).get("count", 0)) if isinstance(row, dict) else 0


def get_workspace_counts(db_path: str | Path | None = None) -> dict[str, int]:
    return {
        "watchlist_items": count_table("watchlist_items", "WHERE active = 1", db_path=db_path),
        "active_alert_rules": count_table("alert_rules", "WHERE active = 1", db_path=db_path),
        "alert_events": count_table("alert_events", db_path=db_path),
        "reports": count_table("report_inbox_items", "WHERE archived = 0", db_path=db_path),
        "strategy_commits": count_table("strategy_commits", "WHERE archived = 0", db_path=db_path),
        "provider_snapshots": count_table("provider_health_snapshots", db_path=db_path),
        "data_quality_snapshots": count_table("data_quality_snapshots", db_path=db_path),
    }


def list_recent_rows(table: str, limit: int = 5, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    allowed = {"alert_events", "report_inbox_items", "strategy_commits", "workspace_activity_log"}
    if table not in allowed:
        raise ValueError(f"Unsupported recent table: {table}")
    order_col = "generated_at" if table == "report_inbox_items" else "created_at"
    return execute_query(f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT ?", (int(limit),), fetch=True, db_path=db_path)  # type: ignore[return-value]

