from __future__ import annotations

from typing import Any

WATCHLIST_PRODUCT_COLUMNS = [
    "item",
    "type",
    "region",
    "latest value",
    "change",
    "volatility state",
    "RMI state",
    "source freshness",
    "data confidence",
    "active alerts",
    "linked events",
    "linked reports",
    "next action",
]


def build_watchlist_table_columns(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for row in rows or []:
        mapped.append(
            {
                "item": row.get("name") or row.get("display_name") or row.get("symbol") or row.get("item_id"),
                "type": row.get("type") or row.get("item_type") or "topic",
                "region": row.get("region") or "Global/unspecified",
                "latest value": row.get("latest_value") if row.get("latest_value") is not None else "N/A",
                "change": row.get("change_pct") if row.get("change_pct") is not None else "N/A",
                "volatility state": row.get("volatility_state") or "unavailable",
                "RMI state": row.get("rmi_state") or row.get("relative_state") or "unavailable",
                "source freshness": row.get("freshness") or row.get("source_status") or "unavailable",
                "data confidence": row.get("data_confidence") or "unknown",
                "active alerts": row.get("active_alert_count", row.get("active_alerts", 0)),
                "linked events": row.get("linked_event_count", row.get("linked_events", 0)),
                "linked reports": row.get("linked_report_count", row.get("linked_reports", 0)),
                "next action": row.get("next_action") or row.get("default_command") or "review detail",
                "item_id": row.get("item_id"),
                "research_only": True,
            }
        )
    return mapped


def build_watchlist_row_badges(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"label": row.get("type") or row.get("item_type") or "topic", "status": "type", "research_only": True},
        {"label": row.get("freshness") or row.get("source_status") or "unavailable", "status": "freshness", "research_only": True},
        {"label": row.get("data_confidence") or "unknown", "status": "confidence", "research_only": True},
    ]
