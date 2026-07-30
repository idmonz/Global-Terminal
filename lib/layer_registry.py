from __future__ import annotations

from typing import Any

from .data_status import FRESHNESS_ESTIMATED, FRESHNESS_FRESH, FRESHNESS_MISSING
from .env_loader import get_env_var
from .provider_health_engine import classify_provider_ledger_status, recommended_action_for_status

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


REQUIRED_LAYER_FIELDS = [
    "layer_id",
    "label",
    "domain",
    "icon",
    "source",
    "provider",
    "is_available",
    "is_estimated",
    "is_optional",
    "requires_key",
    "freshness_status",
    "caveat",
]

RUNTIME_LAYER_FIELDS = [
    "layer_id",
    "label",
    "domain",
    "source",
    "provider",
    "availability",
    "is_available",
    "is_optional",
    "requires_key",
    "row_count",
    "latest_fetched_at",
    "freshness_status",
    "source_status",
    "caveat",
    "recommended_action",
]


def _layer(
    layer_id: str,
    label: str,
    domain: str,
    icon: str,
    source: str,
    provider: str,
    *,
    is_available: bool,
    is_estimated: bool = False,
    is_optional: bool = False,
    requires_key: str | None = None,
    freshness_status: str | None = None,
    caveat: str = "",
) -> dict[str, Any]:
    return {
        "layer_id": layer_id,
        "label": label,
        "domain": domain,
        "icon": icon,
        "source": source,
        "provider": provider,
        "is_available": bool(is_available),
        "is_estimated": bool(is_estimated),
        "is_optional": bool(is_optional),
        "requires_key": requires_key,
        "freshness_status": freshness_status
        or (FRESHNESS_FRESH if is_available and not is_estimated else FRESHNESS_ESTIMATED if is_available else FRESHNESS_MISSING),
        "caveat": caveat,
    }


def build_layer_registry() -> list[dict[str, Any]]:
    """Return the War Room layer registry without implying unavailable live feeds exist."""
    worldmonitor_configured = bool(get_env_var("WORLD_MONITOR_BASE_URL"))
    opensky_configured = bool(get_env_var("OPENSKY_CLIENT_ID") and get_env_var("OPENSKY_CLIENT_SECRET"))
    fmp_configured = bool(get_env_var("FMP_API_KEY"))
    alpha_configured = bool(
        get_env_var("ALPHAVANTAGE_API_KEY")
        or get_env_var("ALPHA_VANTAGE_API_KEY")
    )
    finnhub_configured = bool(get_env_var("FINNHUB_API_KEY"))
    polygon_configured = bool(get_env_var("POLYGON_API_KEY"))
    return [
        _layer("conflicts", "Conflicts", "geopolitical", "alert-triangle", "public news classification", "heuristic", is_available=True, is_estimated=True, caveat="Derived from public headlines when supplied; not an official conflict feed."),
        _layer("protests", "Protests", "geopolitical", "megaphone", "public news classification", "heuristic", is_available=True, is_estimated=True, caveat="Headline keyword layer; event coordinates may be approximate."),
        _layer("sanctions", "Sanctions", "geopolitical", "scale", "OpenSanctions registry slot", "opensanctions", is_available=False, is_optional=True, freshness_status=FRESHNESS_MISSING, caveat="Registry-only in this slice; no live sanctions rows are fetched or displayed."),
        _layer("elections_policy", "Elections / Policy", "geopolitical", "landmark", "public news classification", "heuristic", is_available=True, is_estimated=True, caveat="Policy layer is informational context, not a political forecast."),
        _layer("diplomatic_tensions", "Diplomatic Tensions", "geopolitical", "radio", "public news classification", "heuristic", is_available=True, is_estimated=True, caveat="Signal strength depends on available public headlines."),
        _layer("chokepoints", "Energy Chokepoints", "energy", "ship", "static chokepoint registry", "local", is_available=True, is_estimated=True, caveat="Static registry plus proxy risk; no live vessel tracking."),
        _layer("pipelines", "Pipelines", "energy", "route", "optional infrastructure metadata", "optional", is_available=False, is_optional=True, caveat="No pipeline metadata is bundled in this build."),
        _layer("lng_terminals", "LNG Terminals", "energy", "factory", "optional infrastructure metadata", "optional", is_available=False, is_optional=True, caveat="Displayed as unavailable unless real terminal metadata is added."),
        _layer("oil_storage", "Oil Storage", "energy", "database", "optional infrastructure metadata", "optional", is_available=False, is_optional=True, caveat="No live inventory or tank-level feed is configured."),
        _layer("refineries", "Refineries", "energy", "factory", "optional infrastructure metadata", "optional", is_available=False, is_optional=True, caveat="No refinery outage provider is configured."),
        _layer("power_outages_proxy", "Power Outages Proxy", "infrastructure", "zap", "public news classification", "heuristic", is_available=True, is_estimated=True, caveat="Headline-derived outage proxy only."),
        _layer("internet_outages_proxy", "Internet Outages Proxy", "infrastructure", "wifi-off", "public news classification", "heuristic", is_available=True, is_estimated=True, caveat="Headline-derived outage proxy only."),
        _layer("earthquakes", "Earthquakes", "natural", "activity", "USGS public earthquake feed", "usgs_earthquake", is_available=True, is_estimated=False, requires_key=None, caveat="USGS public feed is queried through the runtime cache; outages surface as unavailable/stale status."),
        _layer("fires", "Wildfires", "natural", "flame", "NASA EONET open-event GeoJSON", "nasa_eonet", is_available=True, caveat="EONET aggregates upstream wildfire sources; verify the event and original source for revisions and scope."),
        _layer("storms_weather_alerts", "Severe Storms", "natural", "cloud-lightning", "NASA EONET open-event GeoJSON", "nasa_eonet", is_available=True, caveat="EONET storm tracks are event context, not a forecast cone or local weather warning."),
        _layer("sea_lake_ice", "Sea / Lake Ice", "natural", "snowflake", "NASA EONET open-event GeoJSON", "nasa_eonet", is_available=True, caveat="Latest EONET track point is shown; no area footprint or climate attribution is inferred."),
        _layer("floods", "Floods", "natural", "waves", "NASA EONET open-event GeoJSON", "nasa_eonet", is_available=True, caveat="EONET aggregates upstream flood reports; boundaries and impact estimates are not provided here."),
        _layer("volcanoes", "Volcanoes", "natural", "mountain", "NASA EONET open-event GeoJSON", "nasa_eonet", is_available=True, caveat="EONET event metadata can revise; inspect the upstream observatory source."),
        _layer("natural_events", "Other Natural Events", "natural", "radar", "NASA EONET open-event GeoJSON", "nasa_eonet", is_available=True, caveat="Fallback category for EONET event types without a dedicated product layer."),
        _layer("climate_anomalies_proxy", "Climate Anomalies Proxy", "natural", "thermometer", "optional climate feed", "optional", is_available=False, is_optional=True, caveat="No climate anomaly provider is bundled."),
        _layer("major_indices", "Major Indices", "market", "line-chart", "yfinance delayed/public data", "yfinance", is_available=True, is_estimated=False, caveat="Availability depends on yfinance connectivity and symbol support."),
        _layer("fx", "FX", "market", "circle-dollar-sign", "yfinance delayed/public data", "yfinance", is_available=True, is_estimated=False, caveat="FX tickers may vary by provider convention."),
        _layer("rates", "Rates", "market", "percent", "yfinance/FRED optional", "public/optional", is_available=True, is_estimated=False, caveat="Treasury proxies are delayed/free where available."),
        _layer("commodities", "Commodities", "market", "bar-chart-3", "yfinance delayed/public data", "yfinance", is_available=True, is_estimated=False, caveat="Futures symbols are delayed/free where available."),
        _layer("crypto", "Crypto Spot", "crypto", "bitcoin", "CoinGecko/Binance public data", "coingecko_public", is_available=True, is_estimated=False, caveat="Exchange and public API availability depends on rate limits and region access."),
        _layer("volatility", "Volatility", "market", "gauge", "yfinance delayed/public data", "yfinance", is_available=True, is_estimated=False, caveat="VIX and volatility proxies are delayed/free where available."),
        _layer("exchange_stress", "Crypto Exchange Stress", "crypto", "server-crash", "optional public/provider feeds", "optional", is_available=False, is_optional=True, caveat="No exchange solvency or proof-of-reserves feed is configured."),
        _layer("oi_funding_stress", "OI / Funding Stress", "crypto", "waves", "Binance public futures endpoints", "binance_futures", is_available=True, is_estimated=False, caveat="Only supported Binance futures symbols are available."),
        _layer("liquidation_pressure_estimate", "Liquidation Pressure Estimate", "crypto", "gauge-circle", "derivatives proxy", "heuristic", is_available=True, is_estimated=True, caveat="Pressure estimate is heuristic and not a liquidation feed."),
        _layer("stablecoin_flow_proxy", "Stablecoin Flow Proxy", "crypto", "coins", "optional on-chain/provider feeds", "optional", is_available=False, is_optional=True, caveat="No real stablecoin flow provider is configured."),
        _layer("ais_unavailable", "AIS Unavailable Marker", "osint", "ship-wheel", "not configured", "none", is_available=False, is_optional=True, requires_key="AIS_PROVIDER_KEY", caveat="No live AIS or vessel tracking is claimed."),
        _layer("flight_tracking_unavailable", "OpenSky Flight Tracking", "osint", "plane", "OpenSky /states/all", "opensky", is_available=opensky_configured, is_optional=True, requires_key="OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET", caveat="Displayed as live only after OpenSky OAuth2 credentials exist and the state-vector fetch succeeds."),
        _layer("live_webcams_optional", "Live Webcams Optional", "osint", "video", "optional public webcam provider", "optional", is_available=False, is_optional=True, requires_key="WEBCAM_PROVIDER_KEY", caveat="No webcam provider is configured."),
        _layer("worldmonitor_optional_adapter", "WorldMonitor Optional Adapter", "osint", "radar", "WORLD_MONITOR_BASE_URL", "worldmonitor", is_available=worldmonitor_configured, is_optional=True, requires_key="WORLD_MONITOR_BASE_URL", caveat="Adapter is optional; local external source tree remains reference-only."),
        _layer("fmp_optional", "FMP Optional Fundamentals", "market", "building-2", "FMP_API_KEY", "fmp", is_available=fmp_configured, is_optional=True, requires_key="FMP_API_KEY", caveat="Optional provider is not required for free-mode operation."),
        _layer("alpha_vantage_optional", "Alpha Vantage Optional", "market", "database", "ALPHAVANTAGE_API_KEY", "alpha_vantage", is_available=alpha_configured, is_optional=True, requires_key="ALPHAVANTAGE_API_KEY", caveat="Optional free-tier provider; ALPHA_VANTAGE_API_KEY remains a compatibility alias."),
        _layer("finnhub_optional", "Finnhub Optional", "market", "radio-receiver", "FINNHUB_API_KEY", "finnhub", is_available=finnhub_configured, is_optional=True, requires_key="FINNHUB_API_KEY", caveat="Optional provider is not required for free-mode operation."),
        _layer("polygon_optional", "Polygon Optional", "market", "hexagon", "POLYGON_API_KEY", "polygon", is_available=polygon_configured, is_optional=True, requires_key="POLYGON_API_KEY", caveat="Optional provider is not required for free-mode operation."),
    ]


def get_default_layers() -> list[str]:
    return [
        layer["layer_id"]
        for layer in build_layer_registry()
        if layer["is_available"] and layer["layer_id"] in {"conflicts", "chokepoints", "earthquakes", "fires", "storms_weather_alerts", "sea_lake_ice", "floods", "volcanoes", "natural_events", "major_indices", "crypto", "oi_funding_stress", "volatility"}
    ]


def filter_layers_by_domain(domain: str) -> list[dict[str, Any]]:
    normalized = (domain or "").strip().lower()
    return [layer for layer in build_layer_registry() if layer["domain"].lower() == normalized]


def filter_layers_by_availability(available: bool = True) -> list[dict[str, Any]]:
    return [layer for layer in build_layer_registry() if layer["is_available"] is bool(available)]


def layer_status_table(layers: list[dict[str, Any]] | None = None):
    rows = list(layers or build_layer_registry())
    if pd is None:
        return rows
    return pd.DataFrame(rows, columns=REQUIRED_LAYER_FIELDS)


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return value.to_dict(orient="records")
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [dict(value)]
    return []


def _status_payload(status: Any) -> dict[str, Any]:
    if hasattr(status, "to_dict"):
        return status.to_dict()
    if isinstance(status, dict):
        return dict(status)
    return {}


def _runtime_statuses(runtime_feeds: dict[str, Any] | None, statuses: list[Any] | None) -> list[Any]:
    output = list(statuses or [])
    if runtime_feeds:
        output.extend(runtime_feeds.get("source_statuses") or [])
        output.extend(runtime_feeds.get("source_status") or [])
    return output


def _latest_fetched_at(rows: list[dict[str, Any]], statuses: list[Any]) -> str | None:
    values = []
    for row in rows:
        if row.get("fetched_at"):
            values.append(str(row["fetched_at"]))
    for status in statuses:
        payload = _status_payload(status)
        if payload.get("fetched_at"):
            values.append(str(payload["fetched_at"]))
    return max(values) if values else None


def _records_layer_ids(row: dict[str, Any]) -> set[str]:
    value = row.get("layer_ids")
    if isinstance(value, list):
        layer_ids = {str(item) for item in value if str(item).strip()}
    elif isinstance(value, str):
        layer_ids = {item.strip() for item in value.split(",") if item.strip()}
    else:
        layer_ids = set()
    provider = str(row.get("provider") or "").lower()
    if not layer_ids and provider in {"usgs_earthquake", "usgs_earthquakes"}:
        layer_ids.add("earthquakes")
    if not layer_ids and provider == "nasa_eonet":
        layer_ids.add("natural_events")
    return layer_ids


def _rows_for_layer(layer_id: str, runtime_feeds: dict[str, Any] | None) -> list[dict[str, Any]]:
    runtime = runtime_feeds or {}
    if layer_id in {"earthquakes", "fires", "storms_weather_alerts", "sea_lake_ice", "floods", "volcanoes", "natural_events"}:
        return [
            row
            for row in _records(runtime.get("natural"))
            if layer_id in _records_layer_ids(row)
        ]
    if layer_id in {"crypto", "oi_funding_stress", "liquidation_pressure_estimate"}:
        return _records(runtime.get("crypto"))
    if layer_id == "flight_tracking_unavailable":
        return _records(runtime.get("flight"))
    if layer_id in {"conflicts", "protests", "elections_policy", "diplomatic_tensions", "power_outages_proxy", "internet_outages_proxy"}:
        return _records(runtime.get("news"))
    if layer_id == "chokepoints":
        try:
            from .event_stream import CHOKEPOINTS

            return _records(CHOKEPOINTS)
        except Exception:
            return []
    return []


def _statuses_for_layer(layer: dict[str, Any], statuses: list[Any]) -> list[Any]:
    provider = str(layer.get("provider") or "").lower()
    layer_id = str(layer.get("layer_id") or "").lower()
    if layer_id in {"conflicts", "protests", "elections_policy", "diplomatic_tensions", "power_outages_proxy", "internet_outages_proxy"}:
        providers = {"live_feeds", "rss", "gdelt"}
    elif layer_id == "earthquakes":
        providers = {"usgs_earthquake", "usgs_earthquakes"}
    elif layer_id in {"fires", "storms_weather_alerts", "sea_lake_ice", "floods", "volcanoes", "natural_events"}:
        providers = {"nasa_eonet"}
    elif layer_id in {"crypto", "oi_funding_stress", "liquidation_pressure_estimate"}:
        providers = {"coingecko_public", "binance_futures", "binance", "coingecko"}
    elif layer_id == "flight_tracking_unavailable":
        providers = {"opensky"}
    else:
        providers = {provider}
    matched = []
    for status in statuses:
        payload = _status_payload(status)
        if str(payload.get("provider") or "").lower() in providers:
            matched.append(status)
    return matched


def _layer_runtime_status(layer: dict[str, Any], rows: list[dict[str, Any]], statuses: list[Any]) -> str:
    if layer.get("layer_id") == "sanctions":
        return "unavailable"
    if layer.get("provider") == "local" or str(layer.get("source", "")).startswith("static"):
        return "proxy/static"
    if statuses:
        ranked = [classify_provider_ledger_status(status) for status in statuses]
        for status in ["forbidden/subscription-blocked", "rate-limited", "missing-key", "stale", "cached", "live/fresh", "proxy/static", "unavailable"]:
            if status in ranked:
                return status
    if not layer.get("is_available"):
        return "missing-key" if layer.get("requires_key") else "unavailable"
    if layer.get("is_estimated"):
        return "proxy/static"
    if rows and _latest_fetched_at(rows, []):
        return "live/fresh"
    return "unavailable"


def build_layer_runtime_payload(
    runtime_feeds: dict[str, Any] | None = None,
    statuses: list[Any] | None = None,
    layers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return JSON-safe map-layer runtime status for Streamlit and future APIs."""
    layer_rows = list(layers or build_layer_registry())
    status_rows = _runtime_statuses(runtime_feeds, statuses)
    runtime_layers = []
    for layer in layer_rows:
        rows = _rows_for_layer(str(layer["layer_id"]), runtime_feeds)
        matched_statuses = _statuses_for_layer(layer, status_rows)
        source_status = _layer_runtime_status(layer, rows, matched_statuses)
        runtime_layers.append(
            {
                "layer_id": layer["layer_id"],
                "label": layer["label"],
                "domain": layer["domain"],
                "source": layer["source"],
                "provider": layer["provider"],
                "availability": "available" if source_status in {"live/fresh", "cached"} else "limited" if source_status in {"stale", "rate-limited", "proxy/static"} else "unavailable",
                "is_available": bool(layer["is_available"] and source_status not in {"missing-key", "unavailable", "forbidden/subscription-blocked"}),
                "is_optional": bool(layer["is_optional"]),
                "requires_key": layer["requires_key"],
                "row_count": len(rows),
                "latest_fetched_at": _latest_fetched_at(rows, matched_statuses),
                "freshness_status": source_status,
                "source_status": source_status,
                "caveat": layer["caveat"],
                "recommended_action": recommended_action_for_status(source_status),
            }
        )
    summary = {
        "layer_count": len(runtime_layers),
        "available_count": sum(1 for layer in runtime_layers if layer["availability"] == "available"),
        "limited_count": sum(1 for layer in runtime_layers if layer["availability"] == "limited"),
        "unavailable_count": sum(1 for layer in runtime_layers if layer["availability"] == "unavailable"),
        "row_count": sum(int(layer["row_count"] or 0) for layer in runtime_layers),
    }
    return {
        "layers": runtime_layers,
        "summary": summary,
        "caveat": "Layer runtime payloads are JSON-safe and never claim live status without freshness evidence.",
    }


def build_layer_ui_payload(search: str = "", domain: str | None = None, *, time_range: str = "24h", region: str = "Global") -> dict[str, Any]:
    query = str(search or "").lower()
    layers = build_layer_registry()
    if domain and domain != "All":
        layers = [layer for layer in layers if layer["domain"].lower() == domain.lower()]
    if query:
        layers = [layer for layer in layers if query in layer["label"].lower() or query in layer["layer_id"].lower() or query in layer["domain"].lower()]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for layer in layers:
        grouped.setdefault(layer["domain"], []).append(layer)
    return {
        "layers": layers,
        "grouped_layers": grouped,
        "available_count": sum(bool(layer["is_available"]) for layer in layers),
        "unavailable_count": sum(not layer["is_available"] for layer in layers),
        "time_range": time_range,
        "time_options": ["1h", "6h", "24h", "7d", "30d", "all"],
        "region": region,
        "region_options": ["Global", "Americas", "Europe", "MENA", "Asia", "Korea", "Energy chokepoints", "Custom"],
        "caveat": "Unavailable layers remain visible and clearly marked unavailable.",
    }


def validate_layer_payload(layer: dict[str, Any] | list[dict[str, Any]]) -> tuple[bool, list[str]]:
    layers = layer if isinstance(layer, list) else [layer]
    issues: list[str] = []
    for idx, item in enumerate(layers):
        missing = [field for field in REQUIRED_LAYER_FIELDS if field not in item]
        if missing:
            issues.append(f"layer[{idx}] missing fields: {', '.join(missing)}")
        if item.get("requires_key") and item.get("is_available") and item.get("provider") in {"none", "optional"}:
            issues.append(f"layer[{idx}] reports available without a configured provider")
    return not issues, issues
