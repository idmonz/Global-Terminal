from __future__ import annotations

import pandas as pd

from lib.portfolio_backtester import build_backtest_result
from lib.portfolio_quant_lab import build_portfolio_source_status, build_strategy_research_payload


def test_portfolio_backtest_accepts_openbb_source_mode_with_supplied_prices():
    prices = pd.DataFrame({"AAA": [100, 101, 103, 102], "BBB": [50, 51, 52, 53]}, index=pd.date_range("2024-01-01", periods=4))

    result, status = build_backtest_result(["AAA", "BBB"], {"AAA": 0.5, "BBB": 0.5}, price_history=prices, source_mode="OpenBB preferred")

    assert status.ok
    assert "portfolio_returns" in result
    assert result["caveat"]


def test_portfolio_source_status_schema(monkeypatch):
    monkeypatch.setattr("lib.portfolio_quant_lab.is_openbb_installed", lambda: False)

    status = build_portfolio_source_status("OpenBB only")

    assert status["source_mode"] == "OpenBB only"
    assert status["openbb_installed"] is False
    assert "no silent fallback" in status["fallback_policy"]


def test_strategy_research_payload_outputs_leaderboard():
    returns = pd.DataFrame({"AAA": [0.01, -0.02, 0.03, 0.01], "BBB": [0.0, 0.01, -0.01, 0.02]}, index=pd.date_range("2024-01-01", periods=4))

    payload = build_strategy_research_payload(returns)

    assert not payload["leaderboard"].empty
    assert "caveat" in payload
