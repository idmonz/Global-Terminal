from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .openbb_factor_backend import build_factor_backend_table, build_symbol_factor_backend
from .portfolio_state import normalize_portfolio_rows, portfolio_rows_to_weights
from .strategy_registry import build_strategy_registry


def build_portfolio_factor_inputs(rows: Any, *, source_mode: str = "auto") -> dict[str, Any]:
    frame = normalize_portfolio_rows(rows)
    weights = portfolio_rows_to_weights(frame)
    symbols = [symbol for symbol in weights if symbol.upper() not in {"CASH", "USD"}]
    factors = build_factor_backend_table(symbols, source_mode=source_mode)
    return {
        "portfolio_rows": frame,
        "weights": weights,
        "symbols": symbols,
        "factors": factors,
        "source_mode": source_mode,
        "caveat": "Portfolio factor inputs are research data and may include proxy-labeled factors.",
    }


def build_asset_factor_profile(symbol: str, *, source_mode: str = "auto") -> dict[str, Any]:
    return build_symbol_factor_backend(symbol, source_mode=source_mode)


def build_portfolio_factor_profile(rows: Any, *, source_mode: str = "auto") -> dict[str, Any]:
    inputs = build_portfolio_factor_inputs(rows, source_mode=source_mode)
    table = inputs["factors"]["table"]
    if pd is None or table is None or getattr(table, "empty", True):
        return {**inputs, "portfolio_scores": {}, "source_confidence": 0.0, "factor_coverage_pct": 0.0}
    weights = inputs["weights"]
    work = table.copy()
    work["weight"] = work["symbol"].map(weights).fillna(0.0)
    score_cols = [col for col in ["value_score", "quality_score", "growth_score", "profitability_score", "options_activity_score", "rates_macro_score"] if col in work.columns]
    scores = {col: round(float((pd.to_numeric(work[col], errors="coerce").fillna(0) * work["weight"]).sum()), 1) for col in score_cols}
    return {
        **inputs,
        "portfolio_scores": scores,
        "source_confidence": round(float((work["source_confidence"].fillna(0) * work["weight"]).sum()), 1),
        "factor_coverage_pct": round(float((work["factor_coverage_pct"].fillna(0) * work["weight"]).sum()), 1),
    }


def build_strategy_factor_matrix(rows: Any, *, source_mode: str = "auto"):
    profile = build_portfolio_factor_profile(rows, source_mode=source_mode)
    scores = profile.get("portfolio_scores", {})
    output = []
    for strategy in build_strategy_registry():
        families = strategy.get("signals_used", [])
        coverage = 0
        for family in families:
            if family in {"value", "quality"}:
                coverage += int(bool(scores.get(f"{family}_score")))
            elif family in {"macro_rotation", "defensive_regime"}:
                coverage += int(bool(scores.get("rates_macro_score")))
            elif family in {"options_aware", "options"}:
                coverage += int(bool(scores.get("options_activity_score")))
            else:
                coverage += int(profile.get("factor_coverage_pct", 0) > 0)
        output.append(
            {
                "strategy": strategy["name"],
                "category": strategy["category"],
                "factor_families": ", ".join(families),
                "factor_coverage_pct": round(coverage / max(1, len(families)) * 100, 1) if families else profile.get("factor_coverage_pct", 0),
                "source_confidence": profile.get("source_confidence", 0),
                "data_quality_penalty": round(max(0.0, 100.0 - profile.get("factor_coverage_pct", 0)), 1),
                "overfit_warning": "Higher risk" if profile.get("factor_coverage_pct", 0) < 50 else "Monitor",
                "caveat": "Strategy factor matrix is a research coverage view.",
            }
        )
    return pd.DataFrame(output) if pd is not None else output


def build_factor_data_gap_report(rows: Any, *, source_mode: str = "auto"):
    profile = build_portfolio_factor_profile(rows, source_mode=source_mode)
    gaps = []
    for symbol, payload in profile["factors"]["payloads"].items():
        for gap in payload.get("data_gaps", []):
            gaps.append(
                {
                    "symbol": symbol,
                    "field": getattr(gap, "field", str(gap)),
                    "reason": getattr(gap, "reason", "data gap"),
                    "severity": getattr(gap, "severity", "medium"),
                }
            )
    return pd.DataFrame(gaps) if pd is not None else gaps
