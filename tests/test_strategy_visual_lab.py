from __future__ import annotations

import pandas as pd

from lib.strategy_visual_lab import strategy_ensemble_equity_curve, strategy_risk_budget_chart


def test_strategy_visual_lab_returns_figures_or_safe_payloads():
    fig = strategy_ensemble_equity_curve(pd.Series([0.01, 0.02]))
    assert fig is not None
    risk_fig = strategy_risk_budget_chart(pd.DataFrame([{"strategy": "A", "risk_contribution": 1.0}]))
    assert risk_fig is not None
