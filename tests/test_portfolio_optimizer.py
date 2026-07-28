from __future__ import annotations

import pandas as pd

from lib.portfolio_optimizer import equal_weight, inverse_volatility_weight, optimize_portfolio_candidates


def test_optimizer_respects_weight_constraints():
    returns = pd.DataFrame({"AAA": [0.01, 0.02, -0.01, 0.01], "BBB": [0.0, 0.01, 0.0, -0.01], "CCC": [0.03, -0.02, 0.01, 0.02]})
    assert sum(equal_weight(["AAA", "BBB"]).values()) == 1
    assert round(sum(inverse_volatility_weight(returns).values()), 8) == 1
    candidates = optimize_portfolio_candidates(returns, max_weight_per_asset=0.6)
    assert not candidates.empty
    assert candidates["max_weight"].max() <= 0.6000001
