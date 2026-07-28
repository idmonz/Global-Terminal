from __future__ import annotations

import pandas as pd

from lib.strategy_risk_budgeting import build_strategy_risk_budget


def test_strategy_risk_budgeting_returns_contributions():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03], "B": [0.0, 0.01, -0.01]})
    budget = build_strategy_risk_budget(returns)
    assert round(budget["table"]["risk_contribution"].sum(), 6) == 1
