from __future__ import annotations

from typing import Any

from .heatmap_drilldown_engine import build_heatmap_command_suggestion
from .heatmap_tile_engine import build_treemap_dataframe, prepare_heatmap_tiles
from .heatmap_tooltip_engine import build_heatmap_tooltip
from .heatmap_visual_theme import build_heatmap_legend, build_heatmap_visual_theme


def build_heatmap_layout(
    rows: Any,
    *,
    title: str = "Heatmap",
    size_mode: str = "market_cap",
    color_mode: str = "daily_change",
    group_mode: str = "sector",
) -> dict[str, Any]:
    tiles = prepare_heatmap_tiles(rows, size_mode=size_mode, color_mode=color_mode, group_mode=group_mode)
    for tile in tiles:
        tile["tooltip"] = build_heatmap_tooltip(tile)
        tile["command_suggestion"] = build_heatmap_command_suggestion(tile)
    return {
        "title": title,
        "size_mode": size_mode,
        "color_mode": color_mode,
        "group_mode": group_mode,
        "tiles": tiles,
        "table": build_treemap_dataframe(tiles),
        "theme": build_heatmap_visual_theme(),
        "legend": build_heatmap_legend(color_mode),
        "data_gap_count": sum(1 for tile in tiles if tile["metadata"]["data_gaps"]),
    }


def build_heatmap_figure_payload(rows: Any, **kwargs: Any) -> dict[str, Any]:
    payload = build_heatmap_layout(rows, **kwargs)
    payload["plotly_spec"] = {
        "type": "treemap",
        "labels": [tile["label"] for tile in payload["tiles"]],
        "parents": [tile["group"] for tile in payload["tiles"]],
        "values": [tile["size"] for tile in payload["tiles"]],
        "colors": [tile["color"] for tile in payload["tiles"]],
        "hovertext": [tile["tooltip"] for tile in payload["tiles"]],
    }
    return payload


def build_provider_health_heatmap(results: Any) -> dict[str, Any]:
    return build_heatmap_layout(results, title="Provider Health Heatmap", size_mode="equal", color_mode="provider_health", group_mode="provider_domain")


def build_source_freshness_heatmap(rows: Any) -> dict[str, Any]:
    return build_heatmap_layout(rows, title="Source Freshness Heatmap", size_mode="equal", color_mode="source_freshness", group_mode="provider_domain")


def build_portfolio_heatmap(rows: Any) -> dict[str, Any]:
    return build_heatmap_layout(rows, title="Portfolio Exposure Heatmap", size_mode="portfolio_weight", color_mode="daily_change", group_mode="portfolio_bucket")


def build_portfolio_risk_heatmap(rows: Any) -> dict[str, Any]:
    return build_heatmap_layout(rows, title="Portfolio Risk Contribution Heatmap", size_mode="risk_contribution", color_mode="risk_score", group_mode="portfolio_bucket")


def build_factor_exposure_heatmap(rows: Any) -> dict[str, Any]:
    return build_heatmap_layout(rows, title="Factor Exposure Heatmap", size_mode="portfolio_weight", color_mode="macro_sensitivity", group_mode="asset_class")


def build_war_room_region_heatmap(rows: Any) -> dict[str, Any]:
    return build_heatmap_layout(rows, title="War Room Region Risk Heatmap", size_mode="event_count", color_mode="war_room_risk", group_mode="region")


def build_energy_risk_heatmap(rows: Any) -> dict[str, Any]:
    return build_heatmap_layout(rows, title="Energy Chokepoint Risk Heatmap", size_mode="risk_score", color_mode="energy_risk", group_mode="chokepoint")
