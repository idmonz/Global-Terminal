from __future__ import annotations

import builtins

import pandas as pd

import lib.equity_scenarios as scenarios
from lib.compliance import contains_forbidden_language


def _history(length=260, start=100.0):
    close = pd.Series([start + i * 0.2 for i in range(length)])
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=length),
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "adj_close": close,
            "volume": [1000 + i for i in range(length)],
        }
    )


def test_technical_diagnostics_and_relative_strength(monkeypatch):
    def fake_history(ticker, period="1y"):
        data = _history(start=100 if ticker != "SPY" else 90)
        return data, scenarios.ok_result(data, source="mock", provider="mock")

    monkeypatch.setattr(scenarios, "_price_history", fake_history)
    data, status = scenarios.compute_equity_technical_diagnostics("AAPL", benchmark="SPY")
    assert status.ok
    assert data["price_vs_50dma"] is not None
    assert "relative_strength_vs_benchmark" in data


def test_options_proxy_missing_data(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yfinance":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    data, status = scenarios.compute_options_chain_proxy("AAPL")
    assert not status.ok
    assert data["data_gaps"]


def test_equity_scenario_matrix_has_four_clean_rows(monkeypatch):
    def fake_history(ticker, period="1y"):
        data = _history()
        return data, scenarios.ok_result(data, source="mock", provider="mock")

    monkeypatch.setattr(scenarios, "_price_history", fake_history)
    monkeypatch.setattr(scenarios, "compute_options_chain_proxy", lambda ticker: ({"ticker": ticker, "data_gaps": ["mock options gap"]}, scenarios.error_result(source="mock", provider="mock", error="mock")))
    frame, status = scenarios.compute_equity_scenario_matrix("AAPL")
    assert status.ok
    assert len(frame) == 4
    assert not contains_forbidden_language(" ".join(frame.astype(str).stack().tolist()))

