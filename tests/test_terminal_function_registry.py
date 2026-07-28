from __future__ import annotations

from lib.terminal_function_registry import build_function_directory_table, get_function_definition, search_functions, validate_command_code


def test_terminal_function_registry_core_codes():
    assert get_function_definition("CC")["label"] == "Command Center"
    assert validate_command_code("AAPL FA")
    assert search_functions("crypto")
    assert "DATA PROBE" in set(build_function_directory_table()["code"])
