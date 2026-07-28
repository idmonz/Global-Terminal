from __future__ import annotations

from typing import Any

from .provider_caveat_panel import build_provider_caveat_panel
from .source_freshness_strip import build_source_freshness_strip
from .watchlist_table_columns import build_watchlist_row_badges


def build_watchlist_detail_panel(item: dict[str, Any] | None = None, *, provider_rows: list[dict[str, Any]] | None = None, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not item:
        return {"title": "No watchlist item selected", "empty": True, "message": "Select an item to inspect linked context.", "research_only": True}
    snapshot = [{"source": item.get("source") or "watchlist", "freshness": item.get("freshness") or item.get("source_status") or "local", "confidence": item.get("data_confidence") or "local"}]
    return {
        "title": item.get("name") or item.get("display_name") or item.get("symbol") or "Watchlist item",
        "item_id": item.get("item_id"),
        "summary": item.get("watch_reason") or item.get("reason") or "Research monitoring item.",
        "badges": build_watchlist_row_badges(item),
        "source_freshness": build_source_freshness_strip(snapshot, title="Item source freshness"),
        "provider_caveats": build_provider_caveat_panel(provider_rows or []),
        "linked_events": events or [],
        "next_actions": ["review detail", "create alert condition", "generate brief"],
        "raw_payload_available": True,
        "research_only": True,
    }
