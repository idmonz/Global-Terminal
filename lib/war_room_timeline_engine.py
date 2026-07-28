from __future__ import annotations

from typing import Any


def build_war_room_timeline(events: list[dict[str, Any]] | None = None, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = sorted(events or [], key=lambda item: str(item.get("timestamp") or item.get("published_at") or ""), reverse=True)
    return [
        {
            "event_id": row.get("event_id"),
            "timestamp": row.get("timestamp") or row.get("published_at"),
            "title": row.get("title"),
            "severity": row.get("severity", "watch"),
            "region": row.get("region", "Global"),
            "source": row.get("source", "unknown"),
            "freshness": row.get("freshness", "unknown"),
            "map_command": f"WAR ROOM {row.get('region', 'Global')}",
        }
        for row in rows[:limit]
    ]


def build_timeline_filters(events: list[dict[str, Any]] | None = None) -> dict[str, list[str]]:
    return {
        "severity": sorted({str(event.get("severity", "watch")) for event in events or []}),
        "region": sorted({str(event.get("region", "Global")) for event in events or []}),
        "source": sorted({str(event.get("source", "unknown")) for event in events or []}),
    }


def connect_timeline_to_map(events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [{**event, "map_marker_id": event.get("event_id") or event.get("title"), "has_map_point": event.get("lat") is not None and event.get("lon") is not None} for event in events or []]
