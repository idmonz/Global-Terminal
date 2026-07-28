from __future__ import annotations

from lib.click_path_engine import build_contextual_drilldowns, build_page_next_actions, build_user_click_map


def test_click_path_engine_uses_neutral_drilldown_language():
    actions = build_page_next_actions("Overview", {"energy": True})
    text = " ".join(action["description"].lower() for action in actions)
    assert "buy" not in text and "sell" not in text
    assert any(action.get("command") for action in actions)
    assert build_contextual_drilldowns({"ticker": "AAPL", "provider": "yfinance"})
    assert build_user_click_map("Overview", {})["clickable_count"] > 0
