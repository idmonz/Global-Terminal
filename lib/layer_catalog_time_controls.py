from __future__ import annotations

from typing import Any

_LAYER_ROWS = [
    ("macro_context", "Macro context", "macro", "public/optional market providers", "fresh", "daily/intraday where available", "global", "provider dependent", "Provider gaps are displayed; no missing data is upgraded."),
    ("market_rows", "Market rows", "markets", "public/optional market providers", "fresh", "intraday where available", "global", "provider dependent", "Unavailable values remain unavailable."),
    ("crypto_stress", "Crypto stress", "crypto", "public crypto providers", "fresh", "intraday where available", "global", "provider dependent", "Derivatives panels depend on configured sources."),
    ("energy_routes", "Energy routes", "energy", "energy/shipping context", "proxy", "daily/proxy", "global chokepoints", "manual refresh", "Proxy or historical-only labels are explicit."),
    ("chokepoint_inventory", "Chokepoint inventory", "chokepoints", "curated static inventory", "historical-only", "static", "global chokepoints", "manual", "Static inventory is not live traffic."),
    ("osint_events", "OSINT events", "osint", "supplied event/news payloads", "source-labeled", "supplied timestamps", "global", "manual/contextual", "Low-confidence events remain unconfirmed."),
    ("provider_health", "Provider health", "provider", "workspace provider snapshots", "fresh", "snapshot based", "provider scope", "manual probe", "Missing credentials are shown explicitly."),
    ("source_freshness", "Source freshness", "source_freshness", "source metadata", "fresh", "snapshot based", "workspace", "manual refresh", "Unknown freshness remains unknown."),
]


def build_layer_catalog(enabled_layers: list[str] | None = None) -> dict[str, Any]:
    enabled = set(enabled_layers or ["macro", "markets", "osint", "provider"])
    layers = []
    for layer_id, display_name, source_type, source, freshness, temporal, spatial, update_frequency, caveat in _LAYER_ROWS:
        layers.append(
            {
                "layer_id": layer_id,
                "display_name": display_name,
                "source": source,
                "source_type": source_type,
                "freshness": freshness,
                "temporal_coverage": temporal,
                "spatial_coverage": spatial,
                "update_frequency": update_frequency,
                "caveat": caveat,
                "enabled": source_type in enabled or layer_id in enabled,
                "requires_key": False,
                "historical_only": freshness == "historical-only",
                "provider_status": "available" if freshness not in {"unavailable", "missing-key"} else freshness,
                "research_only": True,
            }
        )
    return {"title": "Layer catalog", "layers": layers, "enabled_count": sum(1 for row in layers if row["enabled"]), "research_only": True}


def filter_layers_by_preset(layer_catalog: dict[str, Any] | list[dict[str, Any]], preset_layers: list[str] | None = None) -> dict[str, Any]:
    rows = layer_catalog.get("layers", []) if isinstance(layer_catalog, dict) else list(layer_catalog)
    allowed = set(preset_layers or [])
    if not allowed:
        return {"layers": rows, "enabled_count": sum(1 for row in rows if row.get("enabled")), "research_only": True}
    filtered = [{**row, "enabled": row.get("source_type") in allowed or row.get("layer_id") in allowed} for row in rows]
    return {"layers": filtered, "enabled_count": sum(1 for row in filtered if row.get("enabled")), "research_only": True}
