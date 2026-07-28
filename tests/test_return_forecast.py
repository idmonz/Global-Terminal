from __future__ import annotations

import pandas as pd

from lib.return_forecast import FORECAST_CAVEAT, build_expected_return_distribution, historical_mean_forecast


def test_forecast_outputs_include_caveat_and_paths():
    returns = pd.Series([0.01, -0.005, 0.002, 0.004] * 20)
    forecast = historical_mean_forecast(returns, horizon=21)
    distribution = build_expected_return_distribution(returns, method="monte_carlo", horizon=21, simulations=50)

    assert forecast["caveat"] == FORECAST_CAVEAT
    assert distribution["caveat"] == FORECAST_CAVEAT
    assert not distribution["paths"].empty
    assert {"expected_return_estimate", "downside_percentile", "upside_percentile", "median_path", "percentile_paths"}.issubset(distribution)
