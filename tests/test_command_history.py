from __future__ import annotations

from lib.command_history import add_command_history, clear_command_history, get_command_history


def test_command_history_records_and_clears():
    clear_command_history()
    add_command_history("CC", {"status": "routed", "page": "app.py"})
    assert get_command_history()[0]["command"] == "CC"
    clear_command_history()
    assert get_command_history() == []
