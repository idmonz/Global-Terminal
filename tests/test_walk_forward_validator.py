from __future__ import annotations

import pandas as pd

from lib.walk_forward_validator import rolling_train_test_split, run_walk_forward_validation


def test_rolling_train_test_split_schema():
    returns = pd.Series([0.01] * 20, index=pd.date_range("2024-01-01", periods=20))
    splits = rolling_train_test_split(returns, train_window=10, test_window=5)

    assert len(splits) == 2
    assert len(splits[0][0]) == 10
    assert len(splits[0][1]) == 5


def test_walk_forward_validation_outputs_metrics():
    returns = pd.Series([0.01, -0.005, 0.004, 0.002] * 20, index=pd.date_range("2024-01-01", periods=80))
    payload = run_walk_forward_validation(returns, train_window=30, test_window=10)

    assert "windows" in payload
    assert "metrics" in payload
    assert payload["metrics"]["window_count"] > 0
