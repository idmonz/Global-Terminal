from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .data_status import error_result, ok_result


def compute_returns(prices: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    return prices.pct_change().dropna(how="all")


def compute_rolling_sharpe(returns: pd.Series, window: int = 63, risk_free_rate: float = 0.0, annualization: int = 252) -> pd.Series:
    returns = pd.to_numeric(pd.Series(returns), errors="coerce")
    excess = returns - risk_free_rate / annualization
    vol = excess.rolling(window).std()
    sharpe = excess.rolling(window).mean() / vol.replace(0, np.nan) * math.sqrt(annualization)
    return sharpe.replace([np.inf, -np.inf], np.nan)


def compute_sortino(returns: pd.Series, risk_free_rate: float = 0.0, annualization: int = 252) -> float:
    returns = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if returns.empty:
        return float("nan")
    excess = returns - risk_free_rate / annualization
    downside = excess[excess < 0]
    if downside.empty:
        return float("inf") if excess.mean() > 0 else 0.0
    downside_vol = downside.std() * math.sqrt(annualization)
    if downside_vol == 0 or pd.isna(downside_vol):
        return 0.0
    return float(excess.mean() * annualization / downside_vol)


def compute_max_drawdown(prices_or_returns: pd.Series) -> float:
    series = pd.to_numeric(pd.Series(prices_or_returns), errors="coerce").dropna()
    if series.empty:
        return float("nan")
    equity = (1 + series).cumprod() if series.abs().max() < 1 else series
    drawdown = equity / equity.cummax() - 1
    return float(drawdown.min())


def compute_calmar(returns: pd.Series, annualization: int = 252) -> float:
    returns = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if returns.empty:
        return float("nan")
    annual_return = (1 + returns.mean()) ** annualization - 1
    max_dd = abs(compute_max_drawdown(returns))
    if max_dd == 0 or pd.isna(max_dd):
        return float("inf") if annual_return > 0 else 0.0
    return float(annual_return / max_dd)


def compute_realized_volatility(returns: pd.Series, annualization: int = 252) -> float:
    returns = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if returns.empty:
        return float("nan")
    return float(returns.std() * math.sqrt(annualization))


def compute_downside_volatility(returns: pd.Series, annualization: int = 252) -> float:
    returns = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    downside = returns[returns < 0]
    if downside.empty:
        return 0.0
    return float(downside.std() * math.sqrt(annualization))


def compute_historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    returns = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if returns.empty:
        return float("nan")
    quantile = returns.quantile(1 - confidence)
    return float(max(0.0, -quantile))


def compute_historical_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    returns = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if returns.empty:
        return float("nan")
    quantile = returns.quantile(1 - confidence)
    tail = returns[returns <= quantile]
    if tail.empty:
        return compute_historical_var(returns, confidence)
    return float(max(0.0, -tail.mean()))


def compute_beta(asset_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    asset = pd.to_numeric(pd.Series(asset_returns), errors="coerce")
    benchmark = pd.to_numeric(pd.Series(benchmark_returns), errors="coerce")
    aligned = pd.concat([asset, benchmark], axis=1).dropna()
    if aligned.empty or aligned.iloc[:, 1].var() == 0:
        return float("nan")
    return float(aligned.iloc[:, 0].cov(aligned.iloc[:, 1]) / aligned.iloc[:, 1].var())


def compute_correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    if returns is None or returns.empty:
        return pd.DataFrame()
    return returns.corr()


def compute_drawdown_series(prices_or_returns: pd.Series) -> pd.Series:
    series = pd.to_numeric(pd.Series(prices_or_returns), errors="coerce").dropna()
    if series.empty:
        return pd.Series(dtype=float)
    equity = (1 + series).cumprod() if series.abs().max() < 1 else series
    return equity / equity.cummax() - 1


def compute_portfolio_return_series(returns: pd.DataFrame, weights: list[float] | np.ndarray | None = None) -> pd.Series:
    if returns is None or returns.empty:
        return pd.Series(dtype=float)
    frame = returns.dropna(how="all").fillna(0)
    if weights is None:
        weights = np.repeat(1 / len(frame.columns), len(frame.columns))
    weights = np.array(weights, dtype=float)
    if weights.sum() != 0:
        weights = weights / weights.sum()
    return pd.Series(frame.to_numpy() @ weights, index=frame.index, name="portfolio")


def compute_risk_contribution_proxy(returns: pd.DataFrame, weights: list[float] | np.ndarray | None = None) -> pd.DataFrame:
    if returns is None or returns.empty:
        return pd.DataFrame(columns=["asset", "weight", "marginal_risk", "risk_contribution"])
    frame = returns.fillna(0)
    n_assets = len(frame.columns)
    if weights is None:
        weights = np.repeat(1 / n_assets, n_assets)
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum() if weights.sum() else weights
    cov = frame.cov().to_numpy()
    portfolio_vol = math.sqrt(float(weights.T @ cov @ weights)) if n_assets else 0.0
    if portfolio_vol == 0:
        marginal = np.zeros(n_assets)
    else:
        marginal = cov @ weights / portfolio_vol
    contribution = weights * marginal
    total = contribution.sum()
    pct = contribution / total if total else contribution
    return pd.DataFrame({"asset": frame.columns, "weight": weights, "marginal_risk": marginal, "risk_contribution": pct})


def compute_portfolio_risk_score(
    returns: pd.Series,
    *,
    weights: list[float] | None = None,
    beta: float | None = None,
    data_quality_penalty: float = 0.0,
) -> float:
    returns = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if returns.empty:
        return 50.0 + data_quality_penalty
    vol = compute_realized_volatility(returns)
    max_dd = abs(compute_max_drawdown(returns))
    downside = compute_downside_volatility(returns)
    concentration = max(weights) if weights else 1.0
    beta_component = abs(beta) if beta is not None and pd.notna(beta) else 1.0
    score = 20 + min(25, vol * 100) + min(20, max_dd * 100) + min(15, downside * 100) + min(15, concentration * 20) + min(10, beta_component * 5) + data_quality_penalty
    return float(max(0, min(100, score)))


def build_risk_summary(returns: pd.DataFrame | pd.Series, benchmark_returns: pd.Series | None = None, weights: list[float] | None = None) -> tuple[dict[str, Any], object]:
    if isinstance(returns, pd.DataFrame):
        portfolio_returns = compute_portfolio_return_series(returns, weights)
    else:
        portfolio_returns = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if portfolio_returns.empty:
        return {"data_gaps": ["No return history supplied."]}, error_result(source="risk engine", provider="risk", error="No return history supplied.")
    beta = compute_beta(portfolio_returns, benchmark_returns) if benchmark_returns is not None else None
    summary = {
        "volatility": compute_realized_volatility(portfolio_returns),
        "downside_volatility": compute_downside_volatility(portfolio_returns),
        "max_drawdown": compute_max_drawdown(portfolio_returns),
        "var_95": compute_historical_var(portfolio_returns, 0.95),
        "cvar_95": compute_historical_cvar(portfolio_returns, 0.95),
        "sortino": compute_sortino(portfolio_returns),
        "calmar": compute_calmar(portfolio_returns),
        "beta": beta,
        "risk_score": compute_portfolio_risk_score(portfolio_returns, weights=weights, beta=beta),
        "data_gaps": [],
        "confidence_caveat": "Risk metrics are historical estimates and not prediction certainty.",
    }
    return summary, ok_result(summary, source="risk engine", provider="risk", is_estimated=True, coverage=f"{len(portfolio_returns)} return observations")

