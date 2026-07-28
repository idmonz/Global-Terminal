from __future__ import annotations

import pandas as pd

from lib.risk import (
    build_risk_summary,
    compute_beta,
    compute_correlation_matrix,
    compute_historical_cvar,
    compute_historical_var,
    compute_max_drawdown,
    compute_rolling_sharpe,
    compute_sortino,
)


def test_risk_metrics_handle_edges():
    returns = pd.Series([0.01, 0.01, 0.01, 0.01])
    sharpe = compute_rolling_sharpe(returns, window=2)
    assert len(sharpe) == len(returns)
    assert compute_sortino(returns) == float("inf")


def test_var_cvar_beta_correlation_score():
    returns = pd.Series([0.01, -0.02, 0.03, -0.05, 0.02])
    benchmark = pd.Series([0.02, -0.01, 0.02, -0.04, 0.01])
    assert compute_max_drawdown(returns) < 0
    assert compute_historical_var(returns, 0.95) >= 0
    assert compute_historical_cvar(returns, 0.95) >= compute_historical_var(returns, 0.95)
    assert compute_beta(returns, benchmark) == compute_beta(returns, benchmark)
    corr = compute_correlation_matrix(pd.DataFrame({"a": returns, "b": benchmark}))
    assert corr.shape == (2, 2)
    summary, status = build_risk_summary(pd.DataFrame({"a": returns, "b": benchmark}))
    assert status.ok
    assert 0 <= summary["risk_score"] <= 100

