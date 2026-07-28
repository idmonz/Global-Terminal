from lib.command_palette_ui import build_command_palette_state
from lib.research_command_safety import detect_forbidden_command_intent
from lib.terminal_command_router import route_terminal_command


def test_goal11d_blocks_action_intent_in_palette_and_router():
    blocked = ["buy AAPL", "sell BTC", "trade now", "go long BTC", "short ETH", "entry signal", "exit signal", "should buy AAPL", "should sell BTC"]
    for query in blocked:
        assert detect_forbidden_command_intent(query)["blocked"] is True
        state = build_command_palette_state(query)
        assert state["suggestions"][0]["enabled"] is False
        assert state["blocked_card"]["status"] == "blocked"
        assert route_terminal_command(query)["status"] == "blocked"


def test_goal11d_allows_descriptive_market_structure_phrases():
    allowed = ["taker buy/sell ratio", "long/short ratio", "short interest", "short volume", "short squeeze", "order book", "execution quality research"]
    for query in allowed:
        assert detect_forbidden_command_intent(query)["blocked"] is False
        assert route_terminal_command(query)["status"] != "blocked"
