from __future__ import annotations
from typing import Any
from .global_volatility_monitor import build_volatility_ranking


def build_watchlist_volatility_from_enriched(enriched: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    fallback = []
    for row in enriched or []:
        if row.get("realized_volatility_pct") is not None or row.get("drawdown_pct") is not None:
            rows.append({"symbol": row.get("symbol") or row.get("display_name"), "asset_class": row.get("asset_class"), "realized_volatility_pct": row.get("realized_volatility_pct") or 0, "drawdown_pct": row.get("drawdown_pct") or 0, "freshness": row.get("freshness", "unknown"), "source": row.get("source", "watchlist-enriched")})
        else:
            fallback.append({"symbol": row.get("symbol") or row.get("display_name"), "volatility_state": "unavailable", "source": "no volatility context supplied", "freshness": row.get("freshness", "unavailable")})
    ranking = build_volatility_ranking(rows) if rows else []
    return {"title": "Watchlist Volatility Context", "rows": ranking + fallback, "data_source": "Goal 10B volatility adapter with fallback labels", "market_rows_used": len(rows)}
