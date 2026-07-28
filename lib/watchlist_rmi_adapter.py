from __future__ import annotations
from typing import Any
from .relative_market_intelligence import build_rmi_table


def build_watchlist_rmi_from_enriched(enriched: list[dict[str, Any]]) -> dict[str, Any]:
    market_rows = []
    fallback = []
    for row in enriched or []:
        if row.get("latest_value") is not None or row.get("change_pct") is not None:
            market_rows.append({"symbol": row.get("symbol") or row.get("display_name"), "asset_class": row.get("asset_class"), "change_pct": row.get("change_pct") or 0, "return_1m_pct": row.get("return_1m_pct", 0), "realized_volatility_pct": row.get("realized_volatility_pct") or 20, "source": row.get("source", "watchlist-enriched"), "freshness": row.get("freshness", "unknown")})
        else:
            fallback.append({"symbol": row.get("symbol") or row.get("display_name"), "relative_state": "unavailable", "freshness": row.get("freshness", "unavailable"), "reason": "No market context supplied."})
    table = build_rmi_table(market_rows) if market_rows else []
    return {"title": "Watchlist Relative Market Intelligence", "rows": table + fallback, "data_source": "Goal 10B RMI adapter with fallback labels", "market_rows_used": len(market_rows)}
