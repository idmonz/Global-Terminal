from __future__ import annotations

from lib.map_marker_engine import build_chokepoint_marker, build_event_marker, build_map_marker_payload, build_provider_gap_marker, build_vessel_marker


def test_map_marker_engine_does_not_fake_live_vessels():
    vessel = build_vessel_marker({"label": "Unit vessel", "source": "AISStream", "lat": 1, "lon": 2}, provider_status={"ok": False, "live": False})
    assert vessel["freshness"] == "unavailable"
    assert "No live vessel" in vessel["caveat"]
    assert build_event_marker({"title": "Event", "lat": 1, "lon": 2})["marker_type"] == "event"
    assert build_chokepoint_marker({"name": "Hormuz", "lat": 1, "lon": 2})["source"] == "static chokepoint registry"
    assert build_provider_gap_marker({"provider": "NASA"})["truth_label"] == "missing-key"
    assert build_map_marker_payload([{"title": "Event", "lat": 1, "lon": 2}], [{"provider": "NASA"}])["count"] == 2
