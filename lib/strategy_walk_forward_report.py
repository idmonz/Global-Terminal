from __future__ import annotations

from typing import Any

import pandas as pd

from .walk_forward_validator import run_walk_forward_validation


OVERFIT_CAVEAT = "Walk-forward and OOS diagnostics are research-only and can still overfit."


def build_strategy_walk_forward_report(returns: pd.Series | list[float] | None = None) -> dict[str, Any]:
    series = returns if isinstance(returns, pd.Series) else pd.Series(returns or [], dtype=float)
    if series.empty:
        return {"windows": pd.DataFrame(), "metrics": {}, "overfit_warning": True, "caveat": OVERFIT_CAVEAT}
    payload = run_walk_forward_validation(series)
    payload["overfit_warning"] = bool(payload.get("metrics", {}).get("window_count", 0) < 3)
    payload["caveat"] = OVERFIT_CAVEAT
    return payload


def build_oos_decay_summary(is_metrics: dict[str, Any] | None = None, oos_metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    is_score = float((is_metrics or {}).get("risk_adjusted_score", 0) or 0)
    oos_score = float((oos_metrics or {}).get("risk_adjusted_score", 0) or 0)
    decay = 0.0 if is_score == 0 else (is_score - oos_score) / abs(is_score) * 100
    return {"decay_pct": round(decay, 2), "overfit_warning": decay > 50, "caveat": OVERFIT_CAVEAT}
