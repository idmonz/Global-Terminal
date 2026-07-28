from __future__ import annotations

import pandas as pd

from lib.oos_validation import compare_is_oos_decay, compute_oos_metrics, flag_overfit_risk, split_in_sample_out_of_sample


def test_oos_split_and_metrics_schema():
    returns = pd.Series([0.01, -0.005, 0.002, 0.003, -0.001] * 10)
    ins, oos = split_in_sample_out_of_sample(returns, oos_fraction=0.2)
    metrics = compute_oos_metrics(oos)

    assert len(ins) > len(oos)
    assert "observations" in metrics
    assert "caveat" in metrics


def test_overfit_warning_can_be_generated():
    ins = pd.Series([0.02] * 50)
    oos = pd.Series([-0.02] * 20)
    comparison = compare_is_oos_decay(ins, oos)
    warning = flag_overfit_risk(comparison, sharpe_decay_threshold=0.1)

    assert "overfit_risk" in warning
    assert isinstance(warning["flags"], list)
