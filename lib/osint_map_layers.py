from __future__ import annotations

from typing import Any


def build_osint_map_layer_registry() -> list[dict[str, Any]]:
    return [
        {"layer_id": "global_news", "label": "Global news events", "enabled": True, "source": "GDELT/public feeds", "key_required": False, "live": False, "historical_only": False, "proxy": True, "freshness": "estimated", "confidence": 0.55, "marker_style": "circle", "caveat": "Noisy public feed; verify source links."},
        {"layer_id": "conflict_sanctions", "label": "Conflict / sanctions", "enabled": True, "source": "public news/proxy", "key_required": False, "live": False, "historical_only": False, "proxy": True, "freshness": "estimated", "confidence": 0.5, "marker_style": "diamond", "caveat": "Classification is heuristic."},
        {"layer_id": "energy", "label": "Energy / oil / gas", "enabled": True, "source": "static chokepoints + public news", "key_required": False, "live": False, "historical_only": False, "proxy": True, "freshness": "estimated", "confidence": 0.6, "marker_style": "square", "caveat": "No live flows are claimed."},
        {"layer_id": "shipping_chokepoints", "label": "Shipping chokepoints", "enabled": True, "source": "static registry", "key_required": False, "live": False, "historical_only": False, "proxy": True, "freshness": "estimated", "confidence": 0.75, "marker_style": "triangle", "caveat": "Static exposure layer."},
        {"layer_id": "ports", "label": "Ports", "enabled": True, "source": "static registry", "key_required": False, "live": False, "historical_only": False, "proxy": True, "freshness": "estimated", "confidence": 0.65, "marker_style": "circle", "caveat": "Port status is not live unless a provider is configured."},
        {"layer_id": "noaa_accessais", "label": "Historical AIS / NOAA AccessAIS", "enabled": True, "source": "NOAA AccessAIS", "key_required": False, "live": False, "historical_only": True, "proxy": False, "freshness": "historical-only", "confidence": 0.7, "marker_style": "line", "caveat": "Historical-only. No live AIS is claimed."},
        {"layer_id": "aisstream", "label": "AISStream live AIS unavailable", "enabled": False, "source": "AISStream", "key_required": True, "live": False, "historical_only": False, "proxy": False, "freshness": "missing-key", "confidence": 0.0, "marker_style": "ship", "caveat": "Live AIS unavailable unless key exists and probe succeeds."},
        {"layer_id": "opensky", "label": "Flight / OpenSky", "enabled": False, "source": "OpenSky", "key_required": True, "live": False, "historical_only": False, "proxy": False, "freshness": "missing-key", "confidence": 0.0, "marker_style": "aircraft", "caveat": "Live/limited only with credentials or allowed anonymous probe."},
        {"layer_id": "earthquakes", "label": "Earthquakes / USGS", "enabled": True, "source": "USGS", "key_required": False, "live": False, "historical_only": False, "proxy": False, "freshness": "fresh", "confidence": 0.8, "marker_style": "pulse", "caveat": "Feeds can revise after publication."},
        {"layer_id": "weather", "label": "Weather / Open-Meteo", "enabled": True, "source": "Open-Meteo", "key_required": False, "live": False, "historical_only": False, "proxy": True, "freshness": "estimated", "confidence": 0.65, "marker_style": "cloud", "caveat": "Forecast/model context, not observed field report."},
        {"layer_id": "nws_alerts", "label": "NWS U.S. alerts", "enabled": False, "source": "NWS", "key_required": True, "live": False, "historical_only": False, "proxy": False, "freshness": "missing-key", "confidence": 0.0, "marker_style": "alert", "caveat": "Requires descriptive User-Agent."},
        {"layer_id": "nasa_firms", "label": "NASA FIRMS fires", "enabled": False, "source": "NASA FIRMS", "key_required": True, "live": False, "historical_only": False, "proxy": False, "freshness": "missing-key", "confidence": 0.0, "marker_style": "fire", "caveat": "Requires MAP_KEY."},
        {"layer_id": "country_risk", "label": "Country risk", "enabled": True, "source": "country risk model", "key_required": False, "live": False, "historical_only": False, "proxy": True, "freshness": "estimated", "confidence": 0.55, "marker_style": "choropleth", "caveat": "Transparent heuristic score, not official rating."},
        {"layer_id": "crypto_geo", "label": "Crypto/geopolitical events", "enabled": True, "source": "public news/proxy", "key_required": False, "live": False, "historical_only": False, "proxy": True, "freshness": "estimated", "confidence": 0.5, "marker_style": "hex", "caveat": "Asset linkage is heuristic."},
        {"layer_id": "provider_gaps", "label": "Provider/data gaps", "enabled": True, "source": "provider probes", "key_required": False, "live": False, "historical_only": False, "proxy": False, "freshness": "estimated", "confidence": 0.9, "marker_style": "x", "caveat": "Operational diagnostics only."},
    ]


def get_osint_layer(layer_id: str) -> dict[str, Any] | None:
    needle = str(layer_id or "").lower()
    return next((dict(layer) for layer in build_osint_map_layer_registry() if layer["layer_id"] == needle), None)


def build_enabled_osint_layers() -> list[dict[str, Any]]:
    return [layer for layer in build_osint_map_layer_registry() if layer["enabled"]]
