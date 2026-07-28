from __future__ import annotations

import pandas as pd

from lib.compliance import contains_forbidden_language
from lib.data_status import ok_result
from lib.screeners import build_commodity_screener, build_crypto_screener, build_etf_screener, build_stock_screener


def _history():
    dates = pd.date_range("2025-01-01", periods=260)
    return pd.DataFrame({"Close": range(100, 360), "Adj Close": range(100, 360), "Volume": range(1000, 1260)}, index=dates)


def _fake_fetch(tickers, period="1y"):
    return _history(), ok_result(source="mock history", provider="mock", coverage=f"{len(tickers)} tickers")


def test_stock_screener_schema(monkeypatch):
    monkeypatch.setattr("lib.screeners.fetch_multi_history", _fake_fetch)
    frame, status = build_stock_screener()
    assert status.ok
    assert {"ticker", "return_1m_pct", "rsi", "above_50dma", "volume_zscore", "crowding_risk"}.issubset(frame.columns)


def test_etf_crypto_commodity_screeners_no_recommendation_language(monkeypatch):
    monkeypatch.setattr("lib.screeners.fetch_multi_history", _fake_fetch)
    frames = [build_etf_screener()[0], build_crypto_screener()[0], build_commodity_screener()[0]]
    for frame in frames:
        assert not frame.empty
        combined = " ".join(str(value) for value in frame.astype(str).to_numpy().flatten())
        assert not contains_forbidden_language(combined)
