from __future__ import annotations

import pandas as pd

from lib.factor_engine import compute_asset_factor_exposures, compute_factor_returns_proxy, compute_portfolio_factor_exposure


def test_factor_engine_proxy_schema():
    prices = pd.DataFrame({"AAA": [10, 11, 12, 12], "SPY": [100, 101, 103, 104], "QQQ": [80, 81, 83, 84]})
    factor_returns = compute_factor_returns_proxy(prices, {"market": "SPY", "growth_tech": "QQQ"})
    asset_returns = prices[["AAA"]].pct_change().dropna()
    exposures = compute_asset_factor_exposures(asset_returns, factor_returns)
    portfolio = compute_portfolio_factor_exposure(exposures, {"AAA": 1.0})

    assert {"asset", "factor", "beta", "alpha", "r_squared"}.issubset(exposures.columns)
    assert {"factor", "portfolio_beta", "caveat"}.issubset(portfolio.columns)
