from lib.top_command_bar import validate_command_bar_action
from lib.terminal_command_router import route_terminal_command
from lib.command_palette_suggestions import suggest_actions_for_query
from lib.research_workflow_actions import validate_research_workflow_action

BLOCKED = [
    "go long BTC",
    "short ETH",
    "recommend NVDA",
    "best portfolio",
    "guaranteed return strategy",
    "execute order",
]
ALLOWED = [
    "order flow BTC",
    "long-term Treasury",
    "short-term rates",
    "long/short ratio",
    "exit liquidity",
    "entry barrier research",
]


def test_goal12d_command_entry_points_block_same_forbidden_intents():
    for text in BLOCKED:
        assert validate_command_bar_action(text)["blocked"] is True
        assert route_terminal_command(text)["status"] == "blocked"
        assert suggest_actions_for_query(text)[0]["enabled"] is False
        assert validate_research_workflow_action("GENERATE_WATCHLIST_BRIEF", {"query": text})["ok"] is False


def test_goal12d_command_entry_points_allow_research_phrases():
    for text in ALLOWED:
        assert validate_command_bar_action(text)["ok"] is True
        assert route_terminal_command(text)["status"] != "blocked"
        assert suggest_actions_for_query(text)[0].get("enabled", True) is True
        assert validate_research_workflow_action("GENERATE_WATCHLIST_BRIEF", {"query": text})["ok"] is True
