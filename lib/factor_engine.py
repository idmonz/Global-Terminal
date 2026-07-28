from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


FACTOR_PROXIES = {
    "market": "SPY",
    "growth_tech": "QQQ",
    "small_cap": "IWM",
    "value": "VTV",
    "momentum": "MTUM",
    "quality": "QUAL",
    "low_volatility": "USMV",
    "rates_duration": "TLT",
    "credit": "LQD",
    "high_yield": "HYG",
    "usd": "DX-Y.NYB",
    "gold": "GLD",
    "oil": "USO",
    "crypto": "BTC-USD",
}


def _returns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    return frame.apply(pd.to_numeric, errors="coerce").pct_change().dropna(how="all")


def compute_factor_returns_proxy(price_history: pd.DataFrame, factor_proxies: dict[str, str] | None = None) -> pd.DataFrame:
    proxies = factor_proxies or FACTOR_PROXIES
    prices = price_history.copy() if isinstance(price_history, pd.DataFrame) else pd.DataFrame(price_history)
    if "date" in prices.columns:
        prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
        prices = prices.set_index("date")
    columns = {factor: ticker for factor, ticker in proxies.items() if ticker in prices.columns}
    if not columns:
        return pd.DataFrame()
    returns = _returns(prices[list(columns.values())])
    return returns.rename(columns={ticker: factor for factor, ticker in columns.items()})


def compute_regression_alpha_beta(asset_returns: pd.Series, benchmark_returns: pd.Series) -> dict[str, float]:
    aligned = pd.concat([pd.Series(asset_returns).rename("asset"), pd.Series(benchmark_returns).rename("benchmark")], axis=1).dropna()
    if aligned.empty or aligned["benchmark"].var() == 0:
        return {"alpha": float("nan"), "beta": float("nan"), "r_squared": float("nan")}
    beta = float(aligned["asset"].cov(aligned["benchmark"]) / aligned["benchmark"].var())
    alpha = float(aligned["asset"].mean() - beta * aligned["benchmark"].mean())
    corr = aligned.corr().iloc[0, 1]
    return {"alpha": alpha, "beta": beta, "r_squared": float(corr * corr)}


def compute_asset_factor_exposures(asset_returns: pd.DataFrame | pd.Series, factor_returns: pd.DataFrame) -> pd.DataFrame:
    assets = asset_returns.to_frame() if isinstance(asset_returns, pd.Series) else asset_returns
    if assets is None or assets.empty or factor_returns is None or factor_returns.empty:
        return pd.DataFrame(columns=["asset", "factor", "beta", "alpha", "r_squared", "caveat"])
    rows = []
    for asset in assets.columns:
        for factor in factor_returns.columns:
            result = compute_regression_alpha_beta(assets[asset], factor_returns[factor])
            rows.append({"asset": asset, "factor": factor, "beta": result["beta"], "alpha": result["alpha"], "r_squared": result["r_squared"], "caveat": "Factor exposure uses proxy returns and simple regression."})
    return pd.DataFrame(rows)


def compute_portfolio_factor_exposure(asset_exposures: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    if asset_exposures is None or asset_exposures.empty:
        return pd.DataFrame(columns=["factor", "portfolio_beta", "caveat"])
    frame = asset_exposures.copy()
    frame["weight"] = frame["asset"].map(weights).fillna(0.0)
    grouped = frame.groupby("factor").apply(lambda group: float((group["beta"].fillna(0.0) * group["weight"]).sum()), include_groups=False).reset_index(name="portfolio_beta")
    grouped["caveat"] = "Portfolio factor exposure is proxy-based."
    return grouped


def compute_rolling_beta(asset_returns: pd.Series, benchmark_returns: pd.Series, *, window: int = 63) -> pd.Series:
    aligned = pd.concat([pd.Series(asset_returns).rename("asset"), pd.Series(benchmark_returns).rename("benchmark")], axis=1).dropna()
    if aligned.empty:
        return pd.Series(dtype=float)
    covariance = aligned["asset"].rolling(window).cov(aligned["benchmark"])
    variance = aligned["benchmark"].rolling(window).var()
    return (covariance / variance.replace(0, np.nan)).rename("rolling_beta")


def compute_factor_contribution(portfolio_returns: pd.Series, factor_returns: pd.DataFrame, exposures: pd.DataFrame | None = None) -> pd.DataFrame:
    if factor_returns is None or factor_returns.empty:
        return pd.DataFrame(columns=["factor", "estimated_contribution", "caveat"])
    rows = []
    for factor in factor_returns.columns:
        beta = compute_regression_alpha_beta(portfolio_returns, factor_returns[factor])["beta"]
        contribution = float(beta * factor_returns[factor].sum()) if pd.notna(beta) else 0.0
        rows.append({"factor": factor, "estimated_contribution": contribution, "beta": beta, "caveat": "Contribution is a proxy attribution estimate."})
    return pd.DataFrame(rows).sort_values("estimated_contribution", ascending=False)


def build_factor_exposure_table(price_history: pd.DataFrame, asset_returns: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    factor_returns = compute_factor_returns_proxy(price_history)
    exposures = compute_asset_factor_exposures(asset_returns, factor_returns)
    return compute_portfolio_factor_exposure(exposures, weights)


def build_openbb_compatible_factor_backend(rows, *, source_mode: str = "auto") -> dict[str, Any]:
    from .portfolio_factor_router import build_portfolio_factor_profile, build_strategy_factor_matrix

    profile = build_portfolio_factor_profile(rows, source_mode=source_mode)
    return {
        "profile": profile,
        "strategy_factor_matrix": build_strategy_factor_matrix(rows, source_mode=source_mode),
        "caveat": "OpenBB-compatible factor backend keeps OpenBB optional and uses native routes first.",
    }
