from __future__ import annotations

from lib.compliance import contains_forbidden_language
from lib.executive_summary_engine import build_global_executive_summary
from lib.drilldown_recommendation_engine import build_drilldown_cards


def test_goal10_payloads_avoid_trade_directive_language():
    summary = build_global_executive_summary({})
    cards = build_drilldown_cards({})
    text = str(summary) + str(cards)
    assert not contains_forbidden_language(text, allow_disclosure=False)
