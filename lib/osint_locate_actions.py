from __future__ import annotations

from typing import Any


def build_locate_action_payload(event: dict[str, Any] | None = None) -> dict[str, Any]:
    event = event or {}
    lat = event.get("lat") or event.get("latitude")
    lon = event.get("lon") or event.get("longitude")
    inferred = bool(event.get("location_inferred") or event.get("inferred"))
    has_coords = lat is not None and lon is not None
    return {
        "label": "Locate on map" if has_coords else "Locate context unavailable",
        "enabled": has_coords,
        "lat": lat,
        "lon": lon,
        "location_label": event.get("location") or event.get("region") or "unknown",
        "inferred": inferred,
        "caveat": "Location inferred from text." if inferred else ("Coordinates supplied by source." if has_coords else "No coordinates supplied."),
        "target_page": "pages/14_War_Room.py" if has_coords else "",
        "route_payload": {"page": "pages/14_War_Room.py", "lat": lat, "lon": lon, "event_title": event.get("title", "")} if has_coords else {},
        "research_only": True,
    }
