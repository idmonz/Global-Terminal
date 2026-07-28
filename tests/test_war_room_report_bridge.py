from lib.war_room_report_bridge import build_energy_report_snapshot, build_provider_report_snapshot, build_war_room_report_snapshot


def test_war_room_report_bridge():
    assert build_war_room_report_snapshot({"events":[1]})["snapshot_type"] == "war_room"
    assert build_energy_report_snapshot({"chokepoints":["Hormuz"]})["snapshot_type"] == "energy"
    assert build_provider_report_snapshot({"providers":["FRED"]})["snapshot_type"] == "provider"

