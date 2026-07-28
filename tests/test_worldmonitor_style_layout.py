from __future__ import annotations

from lib.terminal_ui import war_room_right_rail_panels
from lib.war_room import build_war_room_state


def test_worldmonitor_style_right_rail_panels_and_state():
    panels = war_room_right_rail_panels({"severity": "high", "freshness": "estimated"})
    names = {panel["title"] for panel in panels}
    for expected in ["Live Intelligence Feed", "AI Brief", "Country Instability", "Chokepoint Risk", "Market Impact", "Crypto Stress", "Provider Health"]:
        assert expected in names
    assert all("caveat" in panel for panel in panels)

    state = build_war_room_state(news=[])
    assert "right_rail" in state
    assert "map_payload" in state
    assert "No live AIS" in " ".join(state["ai_context"]["data_gaps"])
