from __future__ import annotations

from lib.world_event_geocoder import build_geocoded_events, geocode_event, infer_event_location


def test_world_event_geocoder_marks_inferred_locations():
    event = geocode_event({"title": "Red Sea shipping disruption"})
    assert event["has_map_point"] is True
    assert event["truth_label"] == "inferred location"
    assert infer_event_location({"lat": 1, "lon": 2})["location_confidence"] == 0.95
    assert build_geocoded_events([{"title": "Unknown"}])[0]["has_map_point"] is False
