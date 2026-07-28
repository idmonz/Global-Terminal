from __future__ import annotations

from lib.war_room_timeline_engine import build_timeline_filters, build_war_room_timeline, connect_timeline_to_map


def test_war_room_timeline_engine_connects_map_points():
    events = [{"event_id": "1", "title": "A", "region": "MENA", "source": "unit", "lat": 1, "lon": 2}]
    timeline = build_war_room_timeline(events)
    assert timeline[0]["map_command"] == "WAR ROOM MENA"
    assert build_timeline_filters(events)["region"] == ["MENA"]
    assert connect_timeline_to_map(events)[0]["has_map_point"] is True
