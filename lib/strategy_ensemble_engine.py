from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def build_strategy_ensemble_weights(leaderboard: Any, *, score_col: str = "risk_adjusted_score") -> pd.DataFrame:
    frame = leaderboard.copy() if hasattr(leaderboard, "copy") else pd.DataFrame(leaderboard or [])
    if frame.empty:
        return pd.DataFrame(columns=["strategy", "weight"])
    name_col = "candidate" if "candidate" in frame.columns else "name"
    scores = pd.to_numeric(frame.get(score_col, pd.Series(1, index=frame.index)), errors="coerce").fillna(0).clip(lower=0)
    if float(scores.sum()) <= 0:
        scores = pd.Series(1.0, index=frame.index)
    weights = scores / scores.sum()
    return pd.DataFrame({"strategy": frame[name_col].astype(str), "weight": weights.round(6)})


def build_strategy_ensemble_returns(strategy_returns: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    if strategy_returns is None or strategy_returns.empty or weights.empty:
        return pd.Series(dtype=float)
    aligned = weights.set_index("strategy")["weight"]
    columns = [col for col in strategy_returns.columns if col in aligned.index]
    if not columns:
        return pd.Series(dtype=float)
    return strategy_returns[columns].fillna(0).mul(aligned.loc[columns], axis=1).sum(axis=1)


def compute_strategy_ensemble_metrics(returns: pd.Series) -> dict[str, Any]:
    if returns is None or returns.empty:
        return {"periods": 0, "cumulative_return": 0.0, "annualized_volatility": 0.0, "risk_adjusted_score": 0.0}
    cumulative = float((1 + returns.fillna(0)).prod() - 1)
    vol = float(returns.std(ddof=0) * np.sqrt(252)) if len(returns) > 1 else 0.0
    score = float((returns.mean() / returns.std(ddof=0) * np.sqrt(252)) if returns.std(ddof=0) else 0.0)
    return {"periods": int(len(returns)), "cumulative_return": round(cumulative, 6), "annualized_volatility": round(vol, 6), "risk_adjusted_score": round(score, 4), "caveat": "Strategy ensembles are research-only and may overfit."}


def build_strategy_ensemble_report(leaderboard: Any, strategy_returns: pd.DataFrame) -> dict[str, Any]:
    weights = build_strategy_ensemble_weights(leaderboard)
    returns = build_strategy_ensemble_returns(strategy_returns, weights)
    return {"weights": weights, "returns": returns, "metrics": compute_strategy_ensemble_metrics(returns), "caveat": "Research-only ensemble; validate with OOS windows."}
