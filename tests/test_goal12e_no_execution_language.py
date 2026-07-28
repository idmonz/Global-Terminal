from lib.research_command_safety import detect_forbidden_command_intent
from lib.top_command_bar import validate_command_bar_action


def test_goal12e_no_execution_phrases_allowed_through_command_surfaces():
    for text in ["go long BTC", "short ETH", "recommend NVDA", "execute order", "trade now", "rebalance now"]:
        assert detect_forbidden_command_intent(text)["blocked"] is True
        assert validate_command_bar_action(text)["ok"] is False


def test_goal12e_research_phrases_remain_allowed():
    for text in ["order flow BTC", "long-term Treasury", "short-term rates", "long/short ratio", "exit liquidity", "entry barrier research"]:
        assert validate_command_bar_action(text)["ok"] is True
