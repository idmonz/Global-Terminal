from __future__ import annotations

from lib.market_briefing_cards import data_confidence_card, missing_key_card, risk_state_card


def test_market_briefing_cards_are_compact_payloads():
    assert risk_state_card("watch")["title"] == "Risk State"
    assert data_confidence_card(70, ["gap"])["severity"] == "watch"
    assert "FRED_API_KEY" in missing_key_card("FRED_API_KEY")["tags"]
