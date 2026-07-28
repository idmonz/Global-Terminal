from __future__ import annotations

import pandas as pd

from lib.strategy_backtest_engine import build_strategy_leaderboard, run_all_strategy_backtests, run_strategy_candidate_backtest
from lib.strategy_combination_engine import build_strategy_combination_candidates, compute_strategy_ensemble_returns, optimize_strategy_ensemble_weights


def _returns():
    return pd.DataFrame(
        {
            "AAA": [0.01, -0.01, 0.02, 0.01, -0.005, 0.012],
            "BBB": [0.0, 0.005, -0.004, 0.006, 0.002, 0.003],
        },
        index=pd.date_range("2024-01-01", periods=6),
    )


def test_strategy_candidate_backtest_outputs_metrics():
    result = run_strategy_candidate_backtest({"name": "Equal Weight Baseline", "weighting_method": "equal_weight"}, _returns())

    assert result["ok"]
    assert "sharpe" in result["metrics"]
    assert "research" in result["caveat"].lower()


def test_strategy_leaderboard_schema_exists():
    results = run_all_strategy_backtests(_returns(), [{"name": "A", "weighting_method": "equal_weight"}, {"name": "B", "weighting_method": "inverse_volatility"}])
    leaderboard = build_strategy_leaderboard(results)

    assert {"candidate", "risk_adjusted_score", "caveat"}.issubset(leaderboard.columns)


def test_strategy_combination_engine_outputs_candidates_and_weights():
    strategy_returns = pd.DataFrame({"A": [0.01, 0.02, -0.01], "B": [0.0, 0.01, 0.01]})

    weights = optimize_strategy_ensemble_weights(strategy_returns)
    ensemble = compute_strategy_ensemble_returns(strategy_returns, weights)
    candidates = build_strategy_combination_candidates(strategy_returns, ["momentum", "quality"])

    assert round(sum(weights.values()), 6) == 1.0
    assert not ensemble.empty
    assert {"alpha_score", "risk_penalty", "overfit_penalty", "source_confidence"}.issubset(candidates.columns)
