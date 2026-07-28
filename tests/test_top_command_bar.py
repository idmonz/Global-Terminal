from __future__ import annotations

from lib.top_command_bar import build_command_bar_placeholder, build_top_command_bar_state, validate_command_bar_action


def test_top_command_bar_is_research_only():
    state = build_top_command_bar_state("WR")
    assert state["command"] == "WAR ROOM"
    assert state["research_only"] is True
    assert validate_command_bar_action("buy AAPL")["blocked"] is True
    assert "Search" in build_command_bar_placeholder()
