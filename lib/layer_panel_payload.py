from __future__ import annotations

from typing import Any

LAYER_CATALOG = [
    {"layer": "macro", "title": "Macro context", "data_required": "market/macro providers", "caveat": "Delayed or missing provider data is labeled."},
    {"layer": "markets", "title": "Market rows", "data_required": "market providers", "caveat": "No unavailable values are fabricated."},
    {"layer": "crypto", "title": "Crypto stress", "data_required": "crypto public/optional providers", "caveat": "Derivatives context depends on provider availability."},
    {"layer": "energy", "title": "Energy routes", "data_required": "energy and shipping context", "caveat": "Proxy panels are labeled."},
    {"layer": "shipping", "title": "Shipping/chokepoints", "data_required": "AIS or chokepoint proxy", "caveat": "No live vessel claim without configured source."},
    {"layer": "chokepoints", "title": "Chokepoints", "data_required": "curated chokepoint inventory", "caveat": "Static inventory is not live traffic."},
    {"layer": "osint", "title": "OSINT events", "data_required": "supplied event/news payloads", "caveat": "Low-confidence events stay unconfirmed."},
    {"layer": "provider", "title": "Provider health", "data_required": "provider snapshots", "caveat": "Missing credentials are shown explicitly."},
    {"layer": "source_freshness", "title": "Source freshness", "data_required": "source metadata", "caveat": "Unknown freshness is not upgraded."},
]


def build_layer_panel_payload(enabled_layers: list[str] | None = None) -> dict[str, Any]:
    enabled = set(enabled_layers or ["macro", "markets", "osint", "provider"])
    layers = [{**layer, "enabled": layer["layer"] in enabled, "research_only": True} for layer in LAYER_CATALOG]
    return {"title": "Layer panel", "layers": layers, "enabled_count": sum(1 for layer in layers if layer["enabled"]), "research_only": True}
