from __future__ import annotations

from typing import Any

from .live_news_event_pipeline import build_live_news_event_pipeline
from .map_event_clusterer import build_cluster_summary_cards, cluster_events_by_region
from .map_marker_engine import build_map_marker_payload
from .osint_map_layers import build_osint_map_layer_registry
from .war_room_timeline_engine import build_war_room_timeline


def route_osint_provider_data(provider_id: str, payload: Any = None) -> dict[str, Any]:
    provider = str(provider_id or "unknown").lower()
    if provider in {"aisstream", "opensky", "nasa_firms"}:
        return {"provider_id": provider, "status": "missing-key", "items": [], "caveat": "Provider is not shown as live without configured credentials and a successful probe."}
    if provider == "noaa_accessais":
        return {"provider_id": provider, "status": "historical-only", "items": payload or [], "caveat": "NOAA AccessAIS is historical-only."}
    return {"provider_id": provider, "status": "available", "items": payload or [], "caveat": "Source-labeled public or official feed."}


def get_war_room_layer_data(layer_id: str, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    routed = route_osint_provider_data(layer_id, events or [])
    return {"layer_id": layer_id, **routed}


def build_war_room_data_quality_report(layers: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [
        {"layer_id": layer["layer_id"], "label": layer["label"], "freshness": layer["freshness"], "confidence": layer["confidence"], "truth_label": "historical-only" if layer["historical_only"] else "proxy" if layer["proxy"] else "source", "caveat": layer["caveat"]}
        for layer in layers or build_osint_map_layer_registry()
    ]


def build_war_room_missing_key_report(layers: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [
        {"layer_id": layer["layer_id"], "label": layer["label"], "status": "missing-key", "caveat": layer["caveat"]}
        for layer in layers or build_osint_map_layer_registry()
        if layer.get("key_required") and not layer.get("enabled")
    ]


def build_war_room_live_payload(news: Any = None, *, provider_results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pipeline = build_live_news_event_pipeline(news)
    layers = build_osint_map_layer_registry()
    clusters = cluster_events_by_region(pipeline["events"])
    missing_keys = build_war_room_missing_key_report(layers)
    markers = build_map_marker_payload(pipeline["map_events"], missing_keys)
    return {
        "map_layers": layers,
        "events": pipeline["events"],
        "event_timeline": build_war_room_timeline(pipeline["events"]),
        "top_hotspots": build_cluster_summary_cards(clusters),
        "clusters": clusters,
        "source_freshness": build_war_room_data_quality_report(layers),
        "missing_keys": missing_keys,
        "affected_assets": sorted({asset for event in pipeline["events"] for asset in event.get("related_assets", [])}),
        "markers": markers,
        "provider_results": provider_results or [],
        "caveats": [pipeline["caveat"], "AISStream, OpenSky, and NASA FIRMS remain missing-key until configured and probed."],
    }
