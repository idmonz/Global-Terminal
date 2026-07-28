from __future__ import annotations

from typing import Any

import pandas as pd

from .oos_validation import compare_is_oos_decay, compute_oos_metrics, flag_overfit_risk


WF_CAVEAT = "Walk-forward validation is a research diagnostic with rolling historical splits."


def _series(value: Any) -> pd.Series:
    if isinstance(value, pd.Series):
        return pd.to_numeric(value, errors="coerce").dropna()
    frame = pd.DataFrame(value)
    if frame.empty:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame.iloc[:, 0], errors="coerce").dropna()


def rolling_train_test_split(
    returns: Any,
    *,
    train_window: int = 252,
    test_window: int = 63,
    step: int | None = None,
) -> list[tuple[pd.Series, pd.Series]]:
    series = _series(returns)
    if series.empty or len(series) <= train_window:
        return []
    step = step or test_window
    splits = []
    start = 0
    while start + train_window < len(series):
        train = series.iloc[start : start + train_window]
        test = series.iloc[start + train_window : start + train_window + test_window]
        if test.empty:
            break
        splits.append((train, test))
        start += step
    return splits


def compute_walk_forward_metrics(windows: list[dict[str, Any]]) -> dict[str, Any]:
    frame = pd.DataFrame(windows)
    if frame.empty:
        return {"window_count": 0, "caveat": WF_CAVEAT}
    return {
        "window_count": int(len(frame)),
        "median_oos_sharpe": float(frame["oos_sharpe"].median()) if "oos_sharpe" in frame else None,
        "median_oos_cagr": float(frame["oos_cagr"].median()) if "oos_cagr" in frame else None,
        "flagged_windows": int(frame["overfit_flag"].astype(bool).sum()) if "overfit_flag" in frame else 0,
        "caveat": WF_CAVEAT,
    }


def run_walk_forward_validation(
    returns: Any,
    *,
    train_window: int = 252,
    test_window: int = 63,
    step: int | None = None,
) -> dict[str, Any]:
    windows = []
    for idx, (train, test) in enumerate(rolling_train_test_split(returns, train_window=train_window, test_window=test_window, step=step), start=1):
        comparison = compare_is_oos_decay(train, test)
        risk = flag_overfit_risk(comparison)
        oos_metrics = compute_oos_metrics(test)
        windows.append(
            {
                "window": idx,
                "train_start": train.index[0] if len(train) else None,
                "train_end": train.index[-1] if len(train) else None,
                "test_start": test.index[0] if len(test) else None,
                "test_end": test.index[-1] if len(test) else None,
                "oos_sharpe": oos_metrics.get("sharpe"),
                "oos_cagr": oos_metrics.get("cagr"),
                "oos_max_drawdown": oos_metrics.get("max_drawdown"),
                "sharpe_decay": comparison.get("sharpe_decay"),
                "overfit_flag": risk["overfit_risk"] == "elevated",
                "flags": risk["flags"],
                "caveat": WF_CAVEAT,
            }
        )
    return {"windows": pd.DataFrame(windows), "metrics": compute_walk_forward_metrics(windows), "caveat": WF_CAVEAT}
