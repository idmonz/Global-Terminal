from __future__ import annotations

from typing import Any

import pandas as pd

from .strategy_combination_engine import compute_strategy_ensemble_returns, optimize_strategy_ensemble_weights


ALPHA_WORKBENCH_CAVEAT = "Alpha Strategy Workbench is historical research context only. It is not financial advice and does not produce directives."


def _frame(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    return pd.DataFrame(value)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if pd.isna(number):
            return default
        return number
    except Exception:
        return default


def _quality_label(score: float) -> str:
    if score >= 75:
        return "strong sample"
    if score >= 50:
        return "usable sample"
    if score > 0:
        return "thin sample"
    return "data gap"


def _validation_table(research: dict[str, Any], leaderboard: pd.DataFrame) -> pd.DataFrame:
    oos = research.get("oos") or {}
    walk = research.get("walk_forward") or {}
    windows = walk.get("windows", pd.DataFrame())
    window_count = len(windows) if hasattr(windows, "__len__") else 0
    factor_penalty = _number(leaderboard.get("data_quality_penalty", pd.Series([100.0])).min() if not leaderboard.empty else 100.0, 100.0)
    rows = [
        {
            "check": "strategy candidates",
            "status": "available" if not leaderboard.empty else "data gap",
            "value": int(len(leaderboard)),
            "interpretation": "Backtest-ranked research rows are available." if not leaderboard.empty else "Run a backtest to populate strategy rows.",
        },
        {
            "check": "walk-forward windows",
            "status": "available" if window_count else "data gap",
            "value": int(window_count),
            "interpretation": "Rolling validation windows are populated." if window_count else "Rolling validation waits for strategy returns.",
        },
        {
            "check": "OOS decay",
            "status": "monitor" if oos else "data gap",
            "value": oos.get("decay_pct") or oos.get("performance_decay") or 0.0,
            "interpretation": "Compare in-sample and out-of-sample behavior." if oos else "OOS diagnostics wait for strategy returns.",
        },
        {
            "check": "factor/data quality penalty",
            "status": "monitor" if factor_penalty > 25 else "available",
            "value": round(factor_penalty, 1),
            "interpretation": "Lower penalty means stronger factor/source coverage.",
        },
    ]
    return pd.DataFrame(rows)


def build_alpha_strategy_workbench(research: dict[str, Any] | None, factor_profile: dict[str, Any] | None = None, *, max_rows: int = 8) -> dict[str, Any]:
    research = research or {}
    factor_profile = factor_profile or {}
    leaderboard = _frame(research.get("leaderboard"))
    combinations = _frame(research.get("combinations"))
    strategy_returns = _frame(research.get("strategy_returns"))

    if not leaderboard.empty:
        for column in ["risk_adjusted_score", "source_confidence", "factor_coverage_pct", "data_quality_penalty"]:
            if column not in leaderboard.columns:
                leaderboard[column] = 0.0
            leaderboard[column] = pd.to_numeric(leaderboard[column], errors="coerce").fillna(0.0)
        leaderboard["sample_quality"] = leaderboard["risk_adjusted_score"].apply(_quality_label)
        leaderboard["research_rank"] = range(1, len(leaderboard) + 1)
        display_columns = [
            "research_rank",
            "candidate",
            "category",
            "risk_adjusted_score",
            "sample_quality",
            "sharpe",
            "sortino",
            "calmar",
            "max_drawdown",
            "turnover",
            "source_confidence",
            "factor_coverage_pct",
            "data_quality_penalty",
            "overfit_warning",
            "caveat",
        ]
        leaderboard_display = leaderboard[[col for col in display_columns if col in leaderboard.columns]].head(max_rows)
    else:
        leaderboard_display = pd.DataFrame(columns=["research_rank", "candidate", "risk_adjusted_score", "sample_quality", "caveat"])

    ensemble_weights = optimize_strategy_ensemble_weights(strategy_returns) if not strategy_returns.empty else {}
    ensemble_returns = compute_strategy_ensemble_returns(strategy_returns, ensemble_weights) if ensemble_weights else pd.Series(dtype=float, name="strategy_ensemble")
    validation = _validation_table(research, leaderboard)
    coverage = _number(factor_profile.get("factor_coverage_pct"), _number(leaderboard.get("factor_coverage_pct", pd.Series([0.0])).max() if not leaderboard.empty else 0.0))
    confidence = _number(factor_profile.get("source_confidence"), _number(leaderboard.get("source_confidence", pd.Series([0.0])).max() if not leaderboard.empty else 0.0))
    if confidence <= 1:
        confidence *= 100.0

    metrics = [
        {"label": "Candidates", "value": int(len(leaderboard)), "delta": "ranked rows", "freshness": "estimated" if len(leaderboard) else "missing"},
        {"label": "Combinations", "value": int(len(combinations)), "delta": "families", "freshness": "estimated" if len(combinations) else "missing"},
        {"label": "Ensemble Legs", "value": int(len(ensemble_weights)), "delta": "research mix", "freshness": "estimated" if ensemble_weights else "missing"},
        {"label": "Factor Coverage", "value": round(coverage, 1), "delta": "%", "freshness": "estimated" if coverage else "missing"},
        {"label": "Source Confidence", "value": round(confidence, 1), "delta": "score", "freshness": "estimated" if confidence else "missing"},
    ]

    cards = [
        {
            "title": "Alpha Workbench State",
            "summary": f"{len(leaderboard)} ranked strategy candidates and {len(combinations)} alpha combinations are available for historical research.",
            "severity": "watch" if leaderboard.empty else "info",
            "tags": ["alpha", "strategy", "research"],
            "source": "strategy research payload",
            "freshness": "estimated" if not leaderboard.empty else "missing",
        },
        {
            "title": "Validation Lens",
            "summary": "Walk-forward, OOS decay, strategy correlation, and factor coverage should be read together before using a candidate in further research.",
            "severity": "watch",
            "tags": ["walk-forward", "OOS", "factor coverage"],
            "source": "validation payload",
            "freshness": "estimated",
        },
        {
            "title": "Data Quality Lens",
            "summary": f"Factor coverage is {coverage:.1f}% and source confidence is {confidence:.1f}; missing fields remain explicit gaps.",
            "severity": "watch" if coverage < 50 else "info",
            "tags": ["source confidence", "data gaps"],
            "source": "factor backend",
            "freshness": "estimated" if coverage or confidence else "missing",
        },
    ]

    return {
        "metrics": metrics,
        "leaderboard": leaderboard_display,
        "combinations": combinations.head(max_rows),
        "ensemble_weights": pd.DataFrame([{"candidate": key, "weight": value} for key, value in ensemble_weights.items()]),
        "ensemble_returns": ensemble_returns,
        "validation": validation,
        "cards": cards,
        "caveat": ALPHA_WORKBENCH_CAVEAT,
    }
