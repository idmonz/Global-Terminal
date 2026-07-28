from __future__ import annotations

from typing import Any


def build_shipping_chokepoint_layers(chokepoints: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    defaults = chokepoints or [
        {"name": "Strait of Hormuz", "region": "MENA", "risk_score": 70, "lat": 26.6, "lon": 56.25},
        {"name": "Red Sea", "region": "MENA", "risk_score": 65, "lat": 19.5, "lon": 38.5},
        {"name": "Suez Canal", "region": "MENA", "risk_score": 55, "lat": 30.6, "lon": 32.3},
    ]
    return [{**item, "layer_id": "shipping_chokepoints", "freshness": "estimated", "truth_label": "proxy", "caveat": "Static chokepoint exposure; no live vessel flow."} for item in defaults]


def build_port_layer(ports: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [{**port, "layer_id": "ports", "freshness": "estimated", "truth_label": "proxy", "caveat": "Port status is not live unless a provider is configured."} for port in ports or []]


def build_historical_ais_layer(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [{**row, "layer_id": "noaa_accessais", "freshness": "historical-only", "truth_label": "historical-only", "live": False, "caveat": "NOAA AccessAIS is historical-only."} for row in rows or []]


def build_shipping_data_quality_report() -> list[dict[str, Any]]:
    return [
        {"provider": "NOAA AccessAIS", "status": "historical-only", "live": False, "caveat": "Historical archives only."},
        {"provider": "AISStream", "status": "missing-key", "live": False, "caveat": "Live only after key and successful probe."},
        {"provider": "Static chokepoints", "status": "proxy", "live": False, "caveat": "Exposure map only."},
    ]
