from __future__ import annotations

from typing import Any


def _tooltip(kind: str, item: dict[str, Any]) -> str:
    lines = [
        f"Type: {kind}",
        f"Label: {item.get('label') or item.get('title') or item.get('name')}",
        f"Source: {item.get('source', 'unknown')}",
        f"Timestamp: {item.get('timestamp') or item.get('published_at') or item.get('checked_at') or 'N/A'}",
        f"Freshness: {item.get('freshness', 'unknown')}",
        f"Truth label: {item.get('truth_label') or item.get('source_type') or 'unknown'}",
        f"Confidence: {item.get('confidence', 'unknown')}",
        f"Related assets: {item.get('related_assets') or item.get('asset_tags') or item.get('assets') or []}",
        f"Data gaps: {item.get('data_gaps') or item.get('caveat') or 'none reported'}",
        f"Next drilldown: {(item.get('click_action') or {}).get('command') or item.get('command') or 'WAR ROOM'}",
    ]
    return "\n".join(lines)


def build_event_map_tooltip(event: dict[str, Any]) -> str:
    return _tooltip("event", event)


def build_vessel_map_tooltip(vessel: dict[str, Any]) -> str:
    return _tooltip("vessel", vessel)


def build_chokepoint_tooltip(chokepoint: dict[str, Any]) -> str:
    return _tooltip("chokepoint", chokepoint)


def build_weather_tooltip(weather: dict[str, Any]) -> str:
    return _tooltip("weather", weather)


def build_earthquake_tooltip(event: dict[str, Any]) -> str:
    return _tooltip("earthquake", event)


def build_provider_gap_tooltip(gap: dict[str, Any]) -> str:
    return _tooltip("provider_gap", gap)
