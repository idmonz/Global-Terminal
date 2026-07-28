from __future__ import annotations

import pandas as pd

from lib.portfolio_backtester import build_backtest_result, compute_backtest_metrics


def _prices():
    index = pd.date_range("2024-01-01", periods=90, freq="D")
    return pd.DataFrame(
        {
            "AAA": [100 + i * 0.2 for i in range(90)],
            "BBB": [80 + i * 0.1 for i in range(90)],
            "SPY": [400 + i * 0.15 for i in range(90)],
        },
        index=index,
    )


def test_backtest_metrics_schema_and_missing_assets_warning():
    result, status = build_backtest_result(["AAA", "BBB", "MISSING"], {"AAA": 0.5, "BBB": 0.4, "MISSING": 0.1}, price_history=_prices(), benchmark="SPY", rebalance_frequency="monthly")

    assert status.ok
    assert "Missing assets" in status.warning
    assert "MISSING" in result["missing_assets"]
    for key in ["cumulative_return", "cagr", "annualized_volatility", "sharpe", "max_drawdown", "var_95", "cvar_95", "turnover", "transaction_cost_estimate"]:
        assert key in result["metrics"]


def test_transaction_costs_reduce_return_estimate():
    low_cost, _ = build_backtest_result(["AAA", "BBB"], {"AAA": 0.5, "BBB": 0.5}, price_history=_prices(), rebalance_frequency="monthly", transaction_cost_bps=0)
    high_cost, _ = build_backtest_result(["AAA", "BBB"], {"AAA": 0.5, "BBB": 0.5}, price_history=_prices(), rebalance_frequency="monthly", transaction_cost_bps=100)

    assert high_cost["metrics"]["cumulative_return"] <= low_cost["metrics"]["cumulative_return"]
    assert compute_backtest_metrics(low_cost["portfolio_returns"])["positive_month_ratio"] >= 0
