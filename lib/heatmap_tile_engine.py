from __future__ import annotations

from typing import Any, Iterable

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .heatmap_color_scales import classify_heatmap_color_bucket, color_for_bucket


SIZE_COLUMNS = {
    "market_cap": ("market_cap", "size_value"),
    "equal": (),
    "volume": ("volume",),
    "dollar_volume": ("dollar_volume", "volume"),
    "portfolio_weight": ("weight", "portfolio_weight"),
    "risk_contribution": ("risk_contribution", "risk_score"),
    "open_interest": ("open_interest", "oi"),
    "tvl": ("tvl",),
    "provider_coverage": ("coverage", "provider_coverage"),
    "event_count": ("event_count", "count"),
    "risk_score": ("risk_score", "score"),
}

COLOR_COLUMNS = {
    "daily_change": ("daily_return", "change_pct", "return_1d_pct"),
    "weekly_change": ("weekly_return", "return_1w_pct"),
    "monthly_change": ("monthly_return", "return_1m_pct"),
    "volatility": ("realized_vol", "realized_volatility_pct", "volatility"),
    "volume_zscore": ("volume_zscore",),
    "drawdown": ("drawdown_52w", "drawdown_pct"),
    "relative_strength": ("relative_strength", "relative_strength_score"),
    "liquidity_stress": ("liquidity_stress",),
    "funding_rate": ("funding_rate", "funding"),
    "open_interest_change": ("open_interest_change", "oi_change"),
    "liquidation_pressure": ("liquidation_pressure", "liquidation_pressure_score"),
    "data_quality": ("data_quality_score", "quality_score"),
    "provider_health": ("provider_health_score", "score"),
    "source_freshness": ("freshness_score", "age_score"),
    "macro_sensitivity": ("macro_sensitivity",),
    "war_room_risk": ("war_room_risk", "risk_score", "severity_score"),
    "energy_risk": ("energy_risk", "risk_score"),
}

GROUP_COLUMNS = {
    "sector": ("sector", "group"),
    "industry": ("industry", "sector", "group"),
    "asset_class": ("asset_class", "group"),
    "country": ("country", "region", "group"),
    "region": ("region", "country", "group"),
    "exchange": ("exchange", "group"),
    "portfolio_bucket": ("portfolio_bucket", "bucket", "group"),
    "provider_domain": ("domain", "provider_domain", "group"),
    "watchlist_group": ("watchlist_group", "group"),
    "crypto_sector": ("crypto_sector", "category", "group"),
    "event_type": ("event_type", "type", "group"),
    "chokepoint": ("chokepoint", "name", "group"),
}


def _records(rows: Any) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if hasattr(rows, "to_dict"):
        return rows.to_dict(orient="records")
    return [dict(item) for item in rows or []]


def _first_number(row: dict[str, Any], columns: Iterable[str]) -> float | None:
    for column in columns:
        value = row.get(column)
        try:
            if value is not None:
                return float(value)
        except Exception:
            continue
    return None


def compute_tile_size(row: dict[str, Any], size_mode: str = "market_cap") -> dict[str, Any]:
    mode = str(size_mode or "equal")
    if mode == "equal":
        return {"size": 1.0, "mode": mode, "data_gap": None}
    value = _first_number(row, SIZE_COLUMNS.get(mode, (mode,)))
    if value is None or value <= 0:
        return {"size": 1.0, "mode": "equal_fallback", "data_gap": f"missing {mode}"}
    return {"size": max(value, 1.0), "mode": mode, "data_gap": None}


def compute_tile_color_value(row: dict[str, Any], color_mode: str = "daily_change") -> float:
    value = _first_number(row, COLOR_COLUMNS.get(str(color_mode), (str(color_mode),)))
    return 0.0 if value is None else value


def compute_tile_group(row: dict[str, Any], group_mode: str = "sector") -> str:
    for column in GROUP_COLUMNS.get(str(group_mode), (str(group_mode), "group")):
        value = row.get(column)
        if value not in (None, ""):
            return str(value)
    return "Ungrouped"


def compute_tile_label(row: dict[str, Any]) -> str:
    for column in ("symbol", "ticker", "provider_id", "name", "label", "title"):
        value = row.get(column)
        if value not in (None, ""):
            return str(value)
    return "Item"


def compute_tile_metadata(row: dict[str, Any], *, size_gap: str | None = None, color_mode: str = "daily_change") -> dict[str, Any]:
    gaps = list(row.get("data_gaps") or [])
    if isinstance(row.get("data_gap"), str):
        gaps.append(row["data_gap"])
    if size_gap:
        gaps.append(size_gap)
    return {
        "source": row.get("source") or row.get("provider") or "unknown",
        "freshness": row.get("freshness") or row.get("source_freshness") or row.get("status") or "unknown",
        "confidence": row.get("confidence"),
        "truth_label": row.get("truth_label") or row.get("source_type") or row.get("data_quality") or "unknown",
        "data_gaps": sorted(set(str(gap) for gap in gaps if gap)),
        "color_mode": color_mode,
    }


def prepare_heatmap_tiles(
    rows: Any,
    *,
    size_mode: str = "market_cap",
    color_mode: str = "daily_change",
    group_mode: str = "sector",
) -> list[dict[str, Any]]:
    tiles = []
    for row in _records(rows):
        size = compute_tile_size(row, size_mode)
        color_value = compute_tile_color_value(row, color_mode)
        status = row.get("status") or row.get("freshness") or row.get("data_quality")
        bucket = classify_heatmap_color_bucket(color_value, mode=color_mode, status=status)
        tiles.append(
            {
                "id": str(row.get("id") or row.get("symbol") or row.get("ticker") or row.get("provider_id") or row.get("name") or len(tiles)),
                "label": compute_tile_label(row),
                "group": compute_tile_group(row, group_mode),
                "size": size["size"],
                "size_mode": size["mode"],
                "color_value": color_value,
                "color_mode": color_mode,
                "color_bucket": bucket,
                "color": color_for_bucket(bucket),
                "metadata": compute_tile_metadata(row, size_gap=size["data_gap"], color_mode=color_mode),
                "raw": row,
            }
        )
    return tiles


def build_treemap_dataframe(tiles: Iterable[dict[str, Any]]):
    rows = [
        {
            "id": tile["id"],
            "label": tile["label"],
            "group": tile["group"],
            "size": tile["size"],
            "color_value": tile["color_value"],
            "color_bucket": tile["color_bucket"],
            "color": tile["color"],
            "source": tile["metadata"]["source"],
            "freshness": tile["metadata"]["freshness"],
            "truth_label": tile["metadata"]["truth_label"],
            "data_gaps": "; ".join(tile["metadata"]["data_gaps"]),
        }
        for tile in tiles
    ]
    return pd.DataFrame(rows) if pd is not None else rows
