from lib.command_palette_ui import build_command_palette_state
from lib.research_command_safety import detect_forbidden_command_intent, sanitize_research_query
from lib.terminal_command_router import route_terminal_command


ALLOWED = [
    "long-term Treasury",
    "short-term rates",
    "order flow BTC",
    "orderflow BTC",
    "long duration bonds",
    "short duration bonds",
    "limit order book",
    "order book depth",
    "taker buy/sell ratio",
    "long/short ratio",
    "short interest",
]

BLOCKED = [
    "buy AAPL",
    "sell BTC",
    "hold SPY",
    "strong buy NVDA",
    "should sell CL",
    "trade now",
    "go long BTC",
    "go short ETH",
    "long BTC",
    "short ETH",
    "entry signal",
    "exit signal",
    "market order BTC",
    "execute order",
]


def test_goal11e_descriptive_research_phrases_are_allowed_and_preserved():
    for query in ALLOWED:
        safety = detect_forbidden_command_intent(query)
        assert safety["blocked"] is False, query
        assert sanitize_research_query(query) == query
        assert route_terminal_command(query)["status"] != "blocked"


def test_goal11e_market_action_intent_remains_blocked_consistently():
    for query in BLOCKED:
        safety = detect_forbidden_command_intent(query)
        assert safety["blocked"] is True, query
        state = build_command_palette_state(query)
        assert state["blocked_card"]["status"] == "blocked"
        assert state["suggestions"][0]["enabled"] is False
        routed = route_terminal_command(query)
        assert routed["status"] == "blocked"


def test_goal11e_blocked_safe_query_preserves_target_symbol_or_topic():
    assert detect_forbidden_command_intent("buy AAPL")["safe_query"] == "AAPL"
    assert detect_forbidden_command_intent("go long BTC")["safe_query"] == "BTC"
    assert detect_forbidden_command_intent("market order BTC")["safe_query"] == "BTC"
