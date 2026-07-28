from __future__ import annotations

import pandas as pd

from lib.portfolio_visuals import allocation_pie_or_bar, correlation_heatmap, equity_curve_chart, monte_carlo_fan_chart


def test_portfolio_visual_builders_return_figures():
    index = pd.date_range("2024-01-01", periods=10)
    returns = pd.DataFrame({"AAA": [0.01] * 10, "BBB": [-0.002] * 10}, index=index)
    paths = pd.DataFrame({0: [1.0, 1.01, 1.02], 1: [1.0, 0.99, 1.01]})

    assert equity_curve_chart((1 + returns["AAA"]).cumprod()) is not None
    assert allocation_pie_or_bar({"AAA": 0.6, "BBB": 0.4}) is not None
    assert correlation_heatmap(returns) is not None
    assert monte_carlo_fan_chart(paths) is not None
