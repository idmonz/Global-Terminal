from __future__ import annotations
from typing import Any

MARKET_TYPES = {"asset", "equity", "etf", "index", "fx", "rate", "commodity", "crypto"}
REGION_TYPES = {"region", "country", "chokepoint", "port"}
PROVIDER_TYPES = {"provider"}
STRATEGY_TYPES = {"strategy", "portfolio"}
EVENT_TYPES = {"event_theme", "report_topic"}


def route_watchlist_item(item: dict[str, Any]) -> str:
    item_type = str(item.get("item_type") or "asset")
    if item_type in MARKET_TYPES:
        return "market"
    if item_type in REGION_TYPES:
        return "osint"
    if item_type in PROVIDER_TYPES:
        return "provider"
    if item_type in STRATEGY_TYPES:
        return "strategy"
    if item_type in EVENT_TYPES:
        return "event_theme"
    return "metadata"


def default_source_state(route: str) -> dict[str, Any]:
    return {"route": route, "source_status": "unavailable", "freshness": "unavailable", "data_confidence": "missing", "source": "not-supplied"}
