from __future__ import annotations

from lib.shortcut_help import build_shortcut_help_panel, build_shortcut_help_rows, search_shortcuts


def test_shortcut_help_is_searchable():
    assert build_shortcut_help_rows()
    assert search_shortcuts("crypto")
    panel = build_shortcut_help_panel()
    assert "do not execute trades" in panel["summary"].lower()
