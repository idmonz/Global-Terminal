from __future__ import annotations
from typing import Any
try:
    from .heatmap_layout_engine import build_heatmap_layout
except Exception:  # pragma: no cover
    build_heatmap_layout = None


def _score(row: dict[str, Any], mode: str) -> float:
    if mode == "freshness":
        return {"fresh": 90, "live": 95, "supplied": 80, "aging": 55, "stale": 30, "missing-key": 20, "missing_key": 20, "unavailable": 10}.get(str(row.get("freshness", "")).lower(), 45)
    if mode == "data_quality":
        return {"high": 90, "available-data": 75, "supplied": 75, "local": 65, "proxy": 45, "estimated": 45, "missing": 10}.get(str(row.get("data_confidence", "")).lower(), 40)
    if mode == "risk":
        return float(row.get("event_severity") or row.get("guard_warning_count") or abs(float(row.get("realized_volatility_pct") or 0)) or 1)
    return float(row.get("change_pct") or row.get("latest_value") or row.get("event_severity") or row.get("guard_warning_count") or 1)


def build_watchlist_heatmap_from_enriched(enriched: list[dict[str, Any]], *, color_mode: str = "risk") -> dict[str, Any]:
    tiles = []
    for row in enriched or []:
        group = row.get("asset_class") or row.get("region") or row.get("item_type") or "watchlist"
        tiles.append({"label": row.get("symbol") or row.get("display_name"), "group": group, "value": _score(row, color_mode), "freshness": row.get("freshness", "unknown"), "data_confidence": row.get("data_confidence", "unknown"), "source_status": row.get("source_status", "unknown"), "fallback": row.get("source_status") == "unavailable"})
    if build_heatmap_layout and tiles:
        try:
            return build_heatmap_layout(tiles, title="Watchlist Heatmap", size_mode="equal", color_mode="value", group_mode="group")
        except Exception:
            pass
    return {"title": "Watchlist Heatmap", "tiles": tiles, "data_source": "enriched watchlist context", "color_mode": color_mode}
