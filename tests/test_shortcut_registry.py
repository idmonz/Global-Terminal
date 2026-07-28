from __future__ import annotations

from lib.shortcut_registry import build_shortcut_registry, find_shortcut, group_shortcuts_by_workspace, shortcut_to_command


def test_shortcut_registry_maps_workspaces():
    registry = build_shortcut_registry()
    assert find_shortcut("WR")["page"] == "pages/14_War_Room.py"
    assert shortcut_to_command("DP") == "DATA PROBE"
    assert group_shortcuts_by_workspace()
    assert len(registry) >= 6
