from lib.command_palette_suggestions import suggest_actions_for_query
from lib.research_command_safety import detect_forbidden_command_intent
from lib.research_workflow_actions import run_research_workflow_action
from lib.terminal_command_router import route_terminal_command


BLOCKED = [
    "recommend NVDA",
    "recommended portfolio",
    "recommendation TSLA",
    "should recommend AAPL",
    "best portfolio",
    "guaranteed return strategy",
    "guaranteed profit",
    "risk-free return",
    "guaranteed alpha",
    "profit guarantee",
    "buy AAPL",
    "sell BTC",
    "go long BTC",
    "short ETH",
    "execute order",
]

ALLOWED = [
    "hold period analysis",
    "holding period return",
    "exit liquidity",
    "market entry barrier",
    "entry barrier",
    "entry price research",
    "entry/exit distribution analysis",
    "exit liquidity map",
    "taker buy/sell ratio",
    "long/short ratio",
    "order book",
    "order flow",
    "long-term Treasury",
    "short-term rates",
]


def test_goal11f_advisory_and_guarantee_language_is_blocked_consistently(tmp_path):
    for query in BLOCKED:
        safety = detect_forbidden_command_intent(query)
        assert safety["blocked"], query
        assert route_terminal_command(query)["status"] == "blocked", query
        suggestions = suggest_actions_for_query(query)
        assert suggestions[0]["command"] == "BLOCKED_RESEARCH_BOUNDARY", query
        result = run_research_workflow_action("ADD_WATCHLIST_ITEM", {"query": query}, db_path=tmp_path / "workspace.db")
        assert result["status"] == "blocked", query
        assert result["blocked_card"]["safe_alternatives"], query


def test_goal11f_descriptive_research_phrases_are_allowed():
    for query in ALLOWED:
        safety = detect_forbidden_command_intent(query)
        assert not safety["blocked"], query
        assert safety["safe_query"].lower() == query.lower(), query
        assert route_terminal_command(query)["status"] != "blocked", query
        assert suggest_actions_for_query(query)[0]["command"] != "BLOCKED_RESEARCH_BOUNDARY", query
