from __future__ import annotations

from lib.war_room_live_data_router import build_war_room_live_payload, build_war_room_missing_key_report, get_war_room_layer_data, route_osint_provider_data


def test_war_room_live_data_router_builds_truthful_payload():
    payload = build_war_room_live_payload([{"title": "Red Sea shipping risk", "source": "unit"}])
    assert payload["map_layers"]
    assert payload["missing_keys"]
    assert payload["top_hotspots"]
    assert route_osint_provider_data("noaa_accessais")["status"] == "historical-only"
    assert get_war_room_layer_data("aisstream")["status"] == "missing-key"
    assert build_war_room_missing_key_report()
