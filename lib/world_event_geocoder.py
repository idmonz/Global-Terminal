from __future__ import annotations

from typing import Any


REGION_CENTROIDS = {
    "global": (20.0, 0.0),
    "americas": (38.0, -97.0),
    "us": (38.0, -97.0),
    "europe": (50.0, 10.0),
    "mena": (29.0, 43.0),
    "middle east": (29.0, 43.0),
    "asia": (34.0, 100.0),
    "korea": (36.2, 127.8),
    "china": (35.0, 103.0),
    "red sea": (19.5, 38.5),
    "hormuz": (26.6, 56.25),
}


def infer_event_location(event: dict[str, Any]) -> dict[str, Any]:
    if event.get("lat") is not None and event.get("lon") is not None:
        return {"lat": float(event["lat"]), "lon": float(event["lon"]), "location_confidence": 0.95, "location_label": "coordinate", "truth_label": "live" if event.get("live") else "source coordinate"}
    text = " ".join(str(event.get(key, "")) for key in ("location", "country", "region", "title", "summary")).lower()
    for label, (lat, lon) in REGION_CENTROIDS.items():
        if label in text:
            return {"lat": lat, "lon": lon, "location_confidence": 0.55, "location_label": label.title(), "truth_label": "inferred location"}
    return {"lat": None, "lon": None, "location_confidence": 0.0, "location_label": "unknown", "truth_label": "low-confidence geocode"}


def geocode_event(event: dict[str, Any]) -> dict[str, Any]:
    location = infer_event_location(event)
    return {**event, **location, "has_map_point": location["lat"] is not None and location["lon"] is not None and location["location_confidence"] >= 0.5}


def build_geocoded_events(events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [geocode_event(dict(event)) for event in events or []]
