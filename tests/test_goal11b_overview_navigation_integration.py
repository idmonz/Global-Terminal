from lib.research_os_navigation import build_research_os_nav_cards, build_research_os_status_card
from lib.click_path_engine import build_click_path_cards
from lib.terminal_command_router import route_terminal_command
from lib.terminal_function_registry import build_terminal_function_registry


def test_research_os_nav_cards_and_status(tmp_path):
    cards = build_research_os_nav_cards(tmp_path / "research.db")
    commands = {c["command"] for c in cards}
    assert {"WORKSPACE", "WATCHLIST", "REPORTS", "STRATEGY LOG"}.issubset(commands)
    status = build_research_os_status_card(tmp_path / "research.db")
    assert "Personal Research OS" == status["title"]


def test_overview_click_path_includes_goal11_pages():
    cards = build_click_path_cards("app.py")
    pages = {c.get("page") for c in cards}
    assert "pages/19_Research_Workspace.py" in pages
    assert "pages/20_Watchlist_Alerts.py" in pages
    assert "pages/21_Report_Inbox.py" in pages
    assert "pages/22_Strategy_Decision_Log.py" in pages


def test_commands_route_to_research_pages_and_trade_commands_blocked():
    assert route_terminal_command("WORKSPACE")["page"] == "pages/19_Research_Workspace.py"
    assert route_terminal_command("GENERATE WATCHLIST BRIEF")["page"] == "pages/21_Report_Inbox.py"
    assert route_terminal_command("trade now")["ok"] is False
    registry = build_terminal_function_registry()
    assert any(r["code"] == "STRATEGY LOG" for r in registry)
