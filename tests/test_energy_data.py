from __future__ import annotations

import pandas as pd

import lib.energy_data as energy


def test_missing_eia_key_returns_graceful_result(monkeypatch):
    monkeypatch.delenv("EIA_API_KEY", raising=False)
    data, status = energy.get_eia_series("crude_inventories")
    assert data.empty
    assert not status.ok
    assert "EIA_API_KEY" in status.error


def test_eia_parser_normal_and_malformed():
    payload = {"response": {"data": [{"period": "2024-01-01", "value": "10"}]}}
    parsed = energy._parse_eia_payload(payload)
    assert parsed.iloc[0]["value"] == 10
    assert energy._parse_eia_payload({"x": []}).empty


def test_yfinance_energy_fallback_schema(monkeypatch):
    def fake_many(tickers, period="6mo"):
        histories = {ticker: pd.DataFrame({"date": pd.date_range("2024-01-01", periods=2), "close": [10, 11]}) for ticker in list(tickers)[:2]}
        return histories, energy.ok_result(histories, source="mock", provider="mock")

    monkeypatch.setattr(energy, "fetch_many_price_histories", fake_many)
    data, status = energy.get_yfinance_energy_fallback()
    assert status.ok
    assert {"ticker", "latest_price", "daily_return"}.issubset(data.columns)

