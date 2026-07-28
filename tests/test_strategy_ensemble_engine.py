from __future__ import annotations

import pandas as pd

from lib.strategy_ensemble_engine import build_strategy_ensemble_report


def test_strategy_ensemble_returns_metrics():
    leaderboard = pd.DataFrame([{"candidate": "A", "risk_adjusted_score": 70}, {"candidate": "B", "risk_adjusted_score": 30}])
    returns = pd.DataFrame({"A": [0.01, 0.02], "B": [0.0, 0.01]})
    report = build_strategy_ensemble_report(leaderboard, returns)
    assert round(report["weights"]["weight"].sum(), 6) == 1
    assert report["metrics"]["periods"] == 2
