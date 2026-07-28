from lib.terminal_command_router import route_terminal_command
from lib.terminal_function_registry import build_terminal_function_registry
from lib.shortcut_registry import shortcut_to_command


def test_goal11_command_router_routes_research_commands():
    assert route_terminal_command("WORKSPACE")["page"] == "pages/19_Research_Workspace.py"
    assert route_terminal_command("COMMIT STRATEGY")["page"] == "pages/22_Strategy_Decision_Log.py"
    assert route_terminal_command("BUY BTC")["ok"] is False
    assert any(row["code"] == "WATCHLIST" for row in build_terminal_function_registry())
    assert shortcut_to_command("RW") == "WORKSPACE"

