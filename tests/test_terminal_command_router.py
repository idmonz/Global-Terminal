from __future__ import annotations

from lib.terminal_command_router import parse_terminal_command, route_terminal_command


def test_command_router_parses_core_commands():
    assert route_terminal_command("CC")["page"] == "app.py"
    assert route_terminal_command("HELP")["ok"] is True
    assert route_terminal_command("AAPL FA")["symbol"] == "AAPL"
    assert route_terminal_command("BTC CRYPTO")["page"].endswith("8_Crypto_Intelligence.py")
    assert route_terminal_command("DATA PROBE")["page"].endswith("17_Data_Provider_Center.py")


def test_command_router_blocks_order_style_commands():
    result = route_terminal_command("buy AAPL")
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert parse_terminal_command("go short BTC")["blocked"] is True
