from __future__ import annotations

from typing import Any


def build_watchlist_market_context(items: list[dict[str, Any]], market_payloads: dict[str, Any] | None = None) -> dict[str, Any]:
    market_payloads = market_payloads or {}
    rows = []
    for item in items:
        key = item.get("symbol") or item.get("display_name")
        payload = market_payloads.get(key, {}) if isinstance(market_payloads, dict) else {}
        rows.append({
            "item_id": item.get("item_id"),
            "symbol": key,
            "source_status": payload.get("source_status", "unavailable"),
            "freshness": payload.get("freshness", "missing"),
            "confidence": payload.get("confidence", "unknown"),
            "context": payload,
        })
    return {"rows": rows, "data_source": "supplied payloads only", "no_fake_live_data": True}

