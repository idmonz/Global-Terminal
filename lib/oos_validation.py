from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .portfolio_backtester import compute_backtest_metrics


OOS_CAVEAT = "Out-of-sample validation is a research diagnostic and not a prediction."


def _series(value: Any) -> pd.Series:
    if isinstance(value, pd.Series):
        return pd.to_numeric(value, errors="coerce").dropna()
    frame = pd.DataFrame(value)
    if frame.empty:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame.iloc[:, 0], errors="coerce").dropna()


def split_in_sample_out_of_sample(returns: Any, *, oos_fraction: float = 0.3) -> tuple[pd.Series, pd.Series]:
    series = _series(returns)
    if series.empty:
        return series, series
    fraction = min(0.8, max(0.05, float(oos_fraction)))
    split = max(1, min(len(series) - 1, int(len(series) * (1.0 - fraction)))) if len(series) > 1 else len(series)
    return series.iloc[:split], series.iloc[split:]


def compute_oos_metrics(returns: Any) -> dict[str, Any]:
    series = _series(returns)
    metrics = compute_backtest_metrics(series) if not series.empty else {}
    return {**metrics, "observations": int(len(series)), "caveat": OOS_CAVEAT}


def compare_is_oos_decay(in_sample_returns: Any, out_of_sample_returns: Any) -> dict[str, Any]:
    is_metrics = compute_oos_metrics(in_sample_returns)
    oos_metrics = compute_oos_metrics(out_of_sample_returns)
    is_sharpe = float(is_metrics.get("sharpe", np.nan))
    oos_sharpe = float(oos_metrics.get("sharpe", np.nan))
    decay = None if np.isnan(is_sharpe) or np.isnan(oos_sharpe) else is_sharpe - oos_sharpe
    return {
        "in_sample": is_metrics,
        "out_of_sample": oos_metrics,
        "sharpe_decay": decay,
        "cagr_decay": (is_metrics.get("cagr") or 0.0) - (oos_metrics.get("cagr") or 0.0),
        "caveat": OOS_CAVEAT,
    }


def flag_overfit_risk(comparison: dict[str, Any], *, sharpe_decay_threshold: float = 0.75, drawdown_multiplier: float = 1.5) -> dict[str, Any]:
    sharpe_decay = comparison.get("sharpe_decay")
    is_dd = abs(float(comparison.get("in_sample", {}).get("max_drawdown", 0.0) or 0.0))
    oos_dd = abs(float(comparison.get("out_of_sample", {}).get("max_drawdown", 0.0) or 0.0))
    flags = []
    if sharpe_decay is not None and sharpe_decay > sharpe_decay_threshold:
        flags.append("OOS Sharpe decay")
    if is_dd and oos_dd > is_dd * drawdown_multiplier:
        flags.append("OOS drawdown expansion")
    return {
        "overfit_risk": "elevated" if flags else "not flagged",
        "flags": flags,
        "caveat": OOS_CAVEAT,
    }
