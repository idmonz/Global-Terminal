from __future__ import annotations

from lib.market_overview_layout import build_market_overview_payload, build_overview_summary


def test_market_overview_layout_is_summary_first():
    rows = [{"ticker": "SPY", "asset_class": "Equity", "daily_return": 1, "market_cap": 10}]
    payload = build_market_overview_payload(context={"risk_state": "watch", "data_gaps": ["EIA key missing"]}, cross_asset_rows=rows, equity_rows=rows)
    assert payload["summary"]["risk_state"] == "watch"
    assert payload["market_board"]["cross_asset_heatmap"]["tiles"]
    assert payload["click_next"]
    assert build_overview_summary({"key_changes": ["Volatility rose"]})["key_changes"]
