from __future__ import annotations

import pandas as pd

from lib.alpha_combination_search import run_alpha_combination_search


def test_alpha_combination_search_produces_candidates():
    leaderboard = pd.DataFrame(
        [
            {"candidate": "Momentum", "risk_adjusted_score": 70, "factor_coverage_pct": 80},
            {"candidate": "Quality", "risk_adjusted_score": 60, "factor_coverage_pct": 70},
        ]
    )
    result = run_alpha_combination_search(leaderboard)
    assert not result.empty
    assert "Momentum + Quality" in result["name"].iloc[0]
