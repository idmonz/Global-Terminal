from lib.research_command_safety import detect_forbidden_command_intent


def test_goal12d_forbidden_execution_phrases_blocked():
    for text in ['go long BTC', 'short ETH', 'recommend NVDA', 'best portfolio', 'guaranteed return strategy', 'execute order', 'trade now', 'rebalance now']:
        assert detect_forbidden_command_intent(text)['blocked'] is True


def test_goal12d_research_phrases_allowed():
    for text in ['order flow BTC', 'long-term Treasury', 'short-term rates', 'long/short ratio', 'exit liquidity', 'entry barrier research']:
        assert detect_forbidden_command_intent(text)['blocked'] is False
