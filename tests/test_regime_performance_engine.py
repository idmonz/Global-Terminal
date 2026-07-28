from __future__ import annotations

import pandas as pd

from lib.regime_performance_engine import build_regime_performance_table


def test_regime_performance_handles_proxy_regimes():
    returns = pd.DataFrame({"Momentum": [0.01, -0.01]}, index=pd.date_range("2025-01-01", periods=2))
    table = build_regime_performance_table(returns)
    assert set(table["source"]) == {"proxy regime"}
