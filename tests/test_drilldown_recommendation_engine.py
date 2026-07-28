from __future__ import annotations

from lib.compliance import contains_forbidden_language
from lib.drilldown_recommendation_engine import build_drilldown_cards, rank_drilldown_candidates


def test_drilldown_cards_do_not_suggest_trades():
    cards = build_drilldown_cards({"risk_state": "stressed", "data_gaps": ["missing key"]})
    text = " ".join(card["title"] + " " + card["summary"] for card in cards)
    assert cards[0]["command"] == "DATA PROBE" or cards[0]["command"] == "GLOBAL WAR"
    assert not contains_forbidden_language(text, allow_disclosure=False)


def test_rank_drilldowns_descending():
    ranked = rank_drilldown_candidates([{"priority": 1}, {"priority": 5}])
    assert ranked[0]["priority"] == 5
