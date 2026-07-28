from lib.workspace_visuals import build_workspace_quick_action_cards, build_research_only_notice


def test_workspace_visuals():
    assert any(card["command"] == "ADD WATCHLIST" for card in build_workspace_quick_action_cards())
    assert "research" in build_research_only_notice().lower()

