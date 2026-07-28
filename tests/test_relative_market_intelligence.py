from __future__ import annotations

from lib.relative_market_intelligence import build_relative_market_intelligence, compute_relative_strength_score


def test_relative_market_intelligence_builds_table_cards_heatmap():
    rows = [{"ticker": "SPY", "asset_class": "Equity", "daily_return": 1, "monthly_return": 2, "realized_vol": 15}, {"ticker": "TLT", "asset_class": "Rates", "daily_return": -1, "monthly_return": -2, "realized_vol": 20}]
    payload = build_relative_market_intelligence(rows)
    assert payload["table"][0]["relative_strength_score"] >= payload["table"][1]["relative_strength_score"]
    assert payload["cards"]
    assert payload["heatmap"]["tiles"]
    assert compute_relative_strength_score(rows[0]) > 0
