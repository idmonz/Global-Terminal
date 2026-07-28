from __future__ import annotations

import pandas as pd

from lib.strategy_correlation import build_strategy_correlation_heatmap_payload, compute_strategy_drawdown_correlation, compute_strategy_return_correlation


def test_strategy_correlation_payload_contains_matrices():
    returns = pd.DataFrame({"A": [0.01, -0.01, 0.02], "B": [0.0, 0.005, 0.01]})

    ret_corr = compute_strategy_return_correlation(returns)
    dd_corr = compute_strategy_drawdown_correlation(returns)
    payload = build_strategy_correlation_heatmap_payload(returns)

    assert ret_corr.shape == (2, 2)
    assert dd_corr.shape == (2, 2)
    assert {"return_correlation", "drawdown_correlation", "clusters", "caveat"}.issubset(payload)
