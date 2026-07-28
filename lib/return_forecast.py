from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


FORECAST_CAVEAT = "This is a model estimate based on historical/proxy data, not a prediction or investment advice."


def _series(returns: Any) -> pd.Series:
    if isinstance(returns, pd.Series):
        return pd.to_numeric(returns, errors="coerce").dropna()
    frame = pd.DataFrame(returns)
    if frame.empty:
        return pd.Series(dtype=float)
    if frame.shape[1] == 1:
        return pd.to_numeric(frame.iloc[:, 0], errors="coerce").dropna()
    return pd.to_numeric(frame.mean(axis=1), errors="coerce").dropna()


def _summary(method: str, horizon: int, expected: float, volatility: float, data_gaps: list[str] | None = None) -> dict[str, Any]:
    downside = expected - 1.65 * volatility
    upside = expected + 1.65 * volatility
    return {
        "method": method,
        "horizon": horizon,
        "expected_return_estimate": float(expected),
        "volatility_estimate": float(volatility),
        "downside_percentile": float(downside),
        "upside_percentile": float(upside),
        "data_gaps": data_gaps or [],
        "caveat": FORECAST_CAVEAT,
    }


def historical_mean_forecast(returns: Any, *, horizon: int = 252) -> dict[str, Any]:
    series = _series(returns)
    if series.empty:
        return _summary("historical_mean", horizon, 0.0, 0.0, ["No returns supplied."])
    return _summary("historical_mean", horizon, float(series.mean() * horizon), float(series.std() * np.sqrt(horizon)))


def ewma_return_forecast(returns: Any, *, horizon: int = 252, span: int = 63) -> dict[str, Any]:
    series = _series(returns)
    if series.empty:
        return _summary("ewma", horizon, 0.0, 0.0, ["No returns supplied."])
    mean = float(series.ewm(span=span).mean().iloc[-1] * horizon)
    vol = float(series.ewm(span=span).std().iloc[-1] * np.sqrt(horizon))
    return _summary("ewma", horizon, mean, vol)


def momentum_adjusted_forecast(returns: Any, *, horizon: int = 252, lookback: int = 126) -> dict[str, Any]:
    series = _series(returns)
    if series.empty:
        return _summary("momentum_adjusted", horizon, 0.0, 0.0, ["No returns supplied."])
    recent = series.tail(lookback)
    adjustment = float(recent.mean() - series.mean())
    return _summary("momentum_adjusted", horizon, float((series.mean() + adjustment * 0.5) * horizon), float(series.std() * np.sqrt(horizon)))


def factor_model_forecast(returns: Any, factor_expected_returns: dict[str, float] | None = None, exposures: pd.DataFrame | None = None, *, horizon: int = 252) -> dict[str, Any]:
    base = historical_mean_forecast(returns, horizon=horizon)
    if exposures is None or exposures.empty or not factor_expected_returns:
        base["method"] = "factor_model"
        base["data_gaps"].append("Factor expectations or exposures unavailable; using historical fallback.")
        return base
    expected = 0.0
    for _, row in exposures.iterrows():
        expected += float(row.get("portfolio_beta", row.get("beta", 0)) or 0) * float(factor_expected_returns.get(row.get("factor"), 0))
    return _summary("factor_model", horizon, expected, base["volatility_estimate"], [])


def bootstrap_forward_paths(returns: Any, *, horizon: int = 252, simulations: int = 500, seed: int = 7) -> pd.DataFrame:
    series = _series(returns)
    if series.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    samples = rng.choice(series.to_numpy(), size=(horizon, simulations), replace=True)
    paths = np.cumprod(1.0 + samples, axis=0)
    return pd.DataFrame(paths, index=range(1, horizon + 1))


def monte_carlo_forward_paths(returns: Any, *, horizon: int = 252, simulations: int = 500, seed: int = 11) -> pd.DataFrame:
    series = _series(returns)
    if series.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    mean = float(series.mean())
    vol = float(series.std())
    draws = rng.normal(mean, vol, size=(horizon, simulations))
    return pd.DataFrame(np.cumprod(1.0 + draws, axis=0), index=range(1, horizon + 1))


def regime_conditioned_estimate(returns: Any, regimes: pd.Series | None = None, *, active_regime: str | None = None, horizon: int = 252) -> dict[str, Any]:
    series = _series(returns)
    if series.empty or regimes is None or len(regimes) != len(series):
        return _summary("regime_conditioned", horizon, 0.0, 0.0, ["Regime labels unavailable or misaligned."])
    selected = series[pd.Series(regimes, index=series.index).astype(str) == str(active_regime)]
    if selected.empty:
        return _summary("regime_conditioned", horizon, 0.0, 0.0, ["Active regime has no observations."])
    return _summary("regime_conditioned", horizon, float(selected.mean() * horizon), float(selected.std() * np.sqrt(horizon)))


def summarize_forward_distribution(paths: pd.DataFrame, *, horizon: int | None = None) -> dict[str, Any]:
    if paths is None or paths.empty:
        return {"horizon": horizon or 0, "expected_return_estimate": 0.0, "volatility_estimate": 0.0, "downside_percentile": 0.0, "upside_percentile": 0.0, "median_path": [], "percentile_paths": {}, "data_gaps": ["No forward paths supplied."], "caveat": FORECAST_CAVEAT}
    terminal = paths.iloc[-1] - 1.0
    return {
        "horizon": int(horizon or len(paths)),
        "expected_return_estimate": float(terminal.mean()),
        "volatility_estimate": float(terminal.std()),
        "downside_percentile": float(terminal.quantile(0.05)),
        "upside_percentile": float(terminal.quantile(0.95)),
        "median_path": paths.quantile(0.50, axis=1).tolist(),
        "percentile_paths": {"p05": paths.quantile(0.05, axis=1).tolist(), "p25": paths.quantile(0.25, axis=1).tolist(), "p75": paths.quantile(0.75, axis=1).tolist(), "p95": paths.quantile(0.95, axis=1).tolist()},
        "data_gaps": [],
        "caveat": FORECAST_CAVEAT,
    }


def build_expected_return_distribution(returns: Any, *, method: str = "bootstrap", horizon: int = 252, simulations: int = 500) -> dict[str, Any]:
    if method == "monte_carlo":
        paths = monte_carlo_forward_paths(returns, horizon=horizon, simulations=simulations)
    else:
        paths = bootstrap_forward_paths(returns, horizon=horizon, simulations=simulations)
    summary = summarize_forward_distribution(paths, horizon=horizon)
    summary["method"] = method
    summary["paths"] = paths
    return summary
