from __future__ import annotations

from typing import Any

ALERT_OPERATORS = [">", ">=", "<", "<=", "crosses_above", "crosses_below", "changes"]
ALERT_METRICS = ["price", "change_pct", "volatility_state", "rmi_state", "funding_rate", "open_interest", "source_freshness", "provider_status"]


def build_watchlist_alert_builder_payload(item: dict[str, Any] | None = None) -> dict[str, Any]:
    item = item or {}
    return {
        "title": "Alert condition builder",
        "watch_item_id": item.get("item_id", ""),
        "display_name": item.get("name") or item.get("display_name") or item.get("symbol") or "Selected item",
        "metrics": ALERT_METRICS,
        "operators": ALERT_OPERATORS,
        "severity_options": ["watch", "elevated", "high", "critical"],
        "cooldown_minutes_default": 60,
        "expiry_supported": True,
        "dedupe_supported": True,
        "previous_value_supported": True,
        "caveat": "Alert conditions depend on supplied provider context and manual evaluation.",
        "research_only": True,
    }
