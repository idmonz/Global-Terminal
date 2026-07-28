from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd


COMBINATION_CAVEAT = "Alpha combination is a research candidate, not financial advice."


def generate_strategy_combinations(families: list[str] | None = None, *, max_size: int = 3) -> list[dict[str, Any]]:
    families = families or ["momentum", "trend", "low_volatility", "value", "quality", "carry", "macro_rotation", "news_impact"]
    rows = []
    for size in range(1, min(max_size, len(families)) + 1):
        for combo in combinations(families, size):
            rows.append(
                {
                    "name": " + ".join(item.replace("_", " ").title() for item in combo),
                    "families": list(combo),
                    "alpha_score": 50.0 + size * 3.0,
                    "risk_penalty": float(max(0, size - 2) * 4),
                    "turnover_penalty": float(size * 1.5),
                    "data_quality_penalty": 0.0,
                    "overfit_penalty": float(max(0, size - 3) * 8),
                    "regime_fit_score": 50.0,
                    "source_confidence": 0.6,
                    "caveat": COMBINATION_CAVEAT,
                }
            )
    return rows


def compute_strategy_ensemble_returns(strategy_returns: Any, weights: dict[str, float] | None = None) -> pd.Series:
    frame = strategy_returns.copy() if isinstance(strategy_returns, pd.DataFrame) else pd.DataFrame(strategy_returns)
    if frame.empty:
        return pd.Series(dtype=float, name="strategy_ensemble")
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna(how="all").fillna(0.0)
    if weights is None:
        vector = pd.Series(1.0 / len(frame.columns), index=frame.columns)
    else:
        vector = pd.Series(weights, dtype=float).reindex(frame.columns).fillna(0.0)
        vector = vector / vector.sum() if vector.sum() else pd.Series(1.0 / len(frame.columns), index=frame.columns)
    return pd.Series(frame.to_numpy() @ vector.to_numpy(), index=frame.index, name="strategy_ensemble")


def optimize_strategy_ensemble_weights(strategy_returns: Any) -> dict[str, float]:
    frame = strategy_returns.copy() if isinstance(strategy_returns, pd.DataFrame) else pd.DataFrame(strategy_returns)
    if frame.empty:
        return {}
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna(how="all")
    vol = frame.std().replace(0, np.nan)
    mean = frame.mean()
    raw = (mean.clip(lower=0.0) + 0.001) / vol
    raw = raw.replace([np.inf, -np.inf], np.nan).fillna(1.0)
    weights = raw / raw.sum() if raw.sum() else pd.Series(1.0 / len(frame.columns), index=frame.columns)
    return weights.round(6).to_dict()


def build_strategy_combination_candidates(
    strategy_returns: Any,
    families: list[str] | None = None,
    *,
    max_size: int = 3,
) -> pd.DataFrame:
    combos = generate_strategy_combinations(families=families, max_size=max_size)
    frame = strategy_returns.copy() if isinstance(strategy_returns, pd.DataFrame) else pd.DataFrame(strategy_returns)
    source_confidence = 0.35 if frame.empty else min(0.95, max(0.4, frame.notna().mean().mean()))
    rows = []
    for combo in combos:
        score = combo["alpha_score"] + combo["regime_fit_score"] * 0.35 - combo["risk_penalty"] - combo["turnover_penalty"] - combo["data_quality_penalty"] - combo["overfit_penalty"]
        combo = {**combo, "ensemble_weight": round(max(0.0, score) / 100.0, 4), "source_confidence": round(float(source_confidence), 3), "composite_score": round(float(max(0.0, min(100.0, score))), 1)}
        rows.append(combo)
    return pd.DataFrame(rows).sort_values("composite_score", ascending=False).reset_index(drop=True)


def build_factor_aware_strategy_combinations(strategy_returns: Any, factor_profile: dict[str, Any] | None = None, families: list[str] | None = None, *, max_size: int = 3) -> pd.DataFrame:
    frame = build_strategy_combination_candidates(strategy_returns, families=families, max_size=max_size)
    factor_profile = factor_profile or {}
    coverage = float(factor_profile.get("factor_coverage_pct", 0) or 0)
    confidence = float(factor_profile.get("source_confidence", 0) or 0) / 100 if factor_profile.get("source_confidence", 0) > 1 else float(factor_profile.get("source_confidence", 0) or 0)
    if frame.empty:
        return frame
    frame["factor_coverage_pct"] = coverage
    frame["source_confidence"] = round(confidence, 3)
    frame["data_quality_penalty"] = (100 - coverage).clip(lower=0) if hasattr((100 - coverage), "clip") else max(0.0, 100 - coverage)
    frame["composite_score"] = (frame["composite_score"] - max(0.0, 100 - coverage) * 0.08 + confidence * 5).clip(0, 100).round(1)
    frame["overfit_warning"] = "Higher risk" if coverage < 50 else "Monitor"
    return frame.sort_values("composite_score", ascending=False).reset_index(drop=True)
