from __future__ import annotations

import pandas as pd

from lib.data_status import ok_result
from lib.overview import build_cross_asset_cards, build_main_asset_chart_data, build_overview_terminal_data


def _history():
    dates = pd.date_range("2025-01-01", periods=10)
    return pd.DataFrame({"Close": range(100, 110), "Adj Close": range(100, 110), "Volume": range(1000, 1010)}, index=dates)


def _single_ticker_multiindex_history():
    dates = pd.date_range("2025-01-01", periods=60)
    columns = pd.MultiIndex.from_tuples([("Close", "SPY"), ("Open", "SPY"), ("High", "SPY"), ("Low", "SPY"), ("Volume", "SPY")])
    return pd.DataFrame(
        [[100 + idx, 99 + idx, 101 + idx, 98 + idx, 1000 + idx] for idx in range(60)],
        columns=columns,
        index=dates,
    )


def test_cross_asset_cards_schema(monkeypatch):
    monkeypatch.setattr("lib.overview.fetch_multi_history", lambda tickers, period="6mo": (_history(), ok_result(source="mock", provider="mock")))
    cards, status = build_cross_asset_cards()
    assert status.ok
    assert len(cards) >= 12
    assert {"label", "ticker", "price", "change_pct", "data_status"}.issubset(cards.columns)


def test_main_chart_handles_single_ticker_multiindex_close(monkeypatch):
    monkeypatch.setattr("lib.overview.fetch_history", lambda ticker, period="1y": (_single_ticker_multiindex_history(), ok_result(source="mock", provider="mock")))
    frame, status = build_main_asset_chart_data("SPY")
    assert status.ok
    assert "performance_pct" in frame.columns
    assert "drawdown_pct" in frame.columns
    assert "realized_volatility_pct" in frame.columns


def test_overview_data_builder_returns_panels(monkeypatch):
    monkeypatch.setattr("lib.overview.build_cross_asset_cards", lambda period="6mo": (pd.DataFrame([{"label": "VIX", "ticker": "^VIX", "price": 20.0, "change_pct": 0.1}]), ok_result(source="cards", provider="mock")))
    monkeypatch.setattr("lib.overview.build_main_asset_chart_data", lambda ticker, period="1y": (_history(), ok_result(source="chart", provider="mock")))
    monkeypatch.setattr("lib.overview.build_heatmap_strip", lambda: ({"sectors": pd.DataFrame(), "crypto": pd.DataFrame(), "cross_asset": pd.DataFrame()}, ok_result(source="heatmaps", provider="mock")))
    monkeypatch.setattr("lib.overview.build_crypto_mini_panel", lambda: ({"btc_price": 1, "data_gaps": []}, ok_result(source="crypto", provider="mock")))
    monkeypatch.setattr("lib.overview.build_equity_mini_panel", lambda: ({"breadth": 1}, ok_result(source="equity", provider="mock")))
    monkeypatch.setattr("lib.overview.build_energy_geopolitical_mini_panel", lambda: ({"inventory_status": "missing key"}, ok_result(source="energy", provider="mock")))
    monkeypatch.setattr("lib.overview.build_event_news_map", lambda: ({"map": None, "events": pd.DataFrame(), "timeline": pd.DataFrame()}, ok_result(source="map", provider="mock")))
    payload, status = build_overview_terminal_data("SPY")
    assert status.ok
    assert "cards" in payload
    assert "source_statuses" in payload
    assert payload["data_gaps"]
