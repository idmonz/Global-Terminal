from lib.research_command_safety import detect_forbidden_command_intent


def test_goal12c_goal11f_command_safety_still_blocks_actionable_intents():
    for text in ['execute order BTC', 'recommend NVDA', 'best portfolio', 'guaranteed return strategy']:
        assert detect_forbidden_command_intent(text)['blocked'] is True
