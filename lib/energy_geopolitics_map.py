from __future__ import annotations

from typing import Any

from .shipping_map_layers import build_shipping_chokepoint_layers, build_shipping_data_quality_report

try:
    from .energy_market_impact import build_energy_asset_impact_panel as _existing_energy_asset_impact_panel
except Exception:  # pragma: no cover - compatibility fallback
    _existing_energy_asset_impact_panel = None


def build_oil_chokepoint_layer(chokepoints: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return build_shipping_chokepoint_layers(chokepoints)


def build_energy_shipping_layer() -> dict[str, Any]:
    return {"layer_id": "energy_shipping", "status": "proxy", "live": False, "rows": build_shipping_chokepoint_layers(), "caveat": "Shipping layer uses static chokepoints; live AIS is unavailable unless configured and probed."}


def build_energy_weather_layer(weather_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"layer_id": "energy_weather", "status": "estimated", "rows": weather_rows or [], "source": "Open-Meteo/NWS where configured", "caveat": "Weather context is forecast/model or alert data, not vessel telemetry."}


def build_energy_news_event_layer(news_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"layer_id": "energy_news", "status": "proxy", "rows": news_events or [], "source": "GDELT/public feeds", "caveat": "News event classification is heuristic and may be noisy."}


def build_energy_asset_impact_panel(context: dict[str, Any] | None = None) -> dict[str, Any]:
    if _existing_energy_asset_impact_panel is not None:
        return _existing_energy_asset_impact_panel(context or {})
    assets = ["CL=F", "BZ=F", "USO", "XLE", "NG=F"]
    return {"assets": assets, "cards": [{"asset": asset, "impact_label": "watch", "truth_label": "proxy"} for asset in assets], "caveat": "Energy asset impact is proxy-labeled research context."}


def build_energy_risk_summary_cards(context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or {}
    return [
        {"title": "Energy Risk Summary", "summary": str(context.get("summary") or "Chokepoint, weather, and news layers are source-labeled."), "severity": context.get("severity", "watch"), "tags": ["energy", "map"], "freshness": "estimated"},
        {"title": "Shipping Data Truth", "summary": "No fake live shipping data is displayed. NOAA is historical-only; AISStream requires key and probe.", "severity": "watch", "tags": ["AIS", "historical-only"], "freshness": "historical-only"},
    ]


def build_energy_geopolitics_map_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    return {
        "summary_cards": build_energy_risk_summary_cards(context),
        "chokepoint_layer": build_oil_chokepoint_layer(context.get("chokepoints")),
        "shipping_layer": build_energy_shipping_layer(),
        "weather_layer": build_energy_weather_layer(context.get("weather_rows")),
        "news_layer": build_energy_news_event_layer(context.get("news_events")),
        "asset_impact_panel": build_energy_asset_impact_panel(context),
        "data_quality": build_shipping_data_quality_report(),
        "related_assets": ["CL=F", "BZ=F", "USO", "XLE", "NG=F", "tanker/shipping proxies"],
    }
