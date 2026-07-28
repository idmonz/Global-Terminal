from __future__ import annotations

from typing import Any


REPORT_CARD_CAVEAT = "Strategy report card is research context only and is not financial advice."


def build_strategy_summary_card(candidate: dict[str, Any]) -> dict[str, Any]:
    metrics = candidate.get("metrics", candidate)
    return {
        "title": candidate.get("candidate") or candidate.get("name") or "Strategy candidate",
        "label": "Research candidate",
        "score": candidate.get("risk_adjusted_score") or metrics.get("risk_adjusted_score"),
        "signals_used": candidate.get("signals_used", []),
        "assets_selected": candidate.get("assets_selected", list(candidate.get("weights", {}).keys())),
        "weights": candidate.get("weights", {}),
        "rebalance_rule": candidate.get("rebalance_rule") or candidate.get("rebalance_frequency"),
        "source_confidence": candidate.get("source_confidence", 0.5),
        "caveat": REPORT_CARD_CAVEAT,
    }


def build_strategy_risk_card(candidate: dict[str, Any]) -> dict[str, Any]:
    metrics = candidate.get("metrics", candidate)
    return {
        "title": "Risk profile",
        "max_drawdown": metrics.get("max_drawdown"),
        "volatility": metrics.get("annualized_volatility"),
        "var_95": metrics.get("var_95"),
        "cvar_95": metrics.get("cvar_95"),
        "turnover": metrics.get("turnover"),
        "risk_controls": candidate.get("risk_controls", []),
        "caveat": REPORT_CARD_CAVEAT,
    }


def build_strategy_data_gap_card(candidate: dict[str, Any]) -> dict[str, Any]:
    gaps = candidate.get("data_gaps", [])
    return {
        "title": "Data quality",
        "data_gaps": gaps,
        "data_quality_penalty": candidate.get("data_quality_penalty", 0.0 if not gaps else 10.0),
        "source_confidence": candidate.get("source_confidence", 1.0 if not gaps else 0.45),
        "caveat": "Missing data remains a visible gap and is not filled with fabricated values.",
    }


def build_strategy_overfit_warning_card(candidate: dict[str, Any]) -> dict[str, Any]:
    oos = candidate.get("oos_metrics", {})
    overfit = candidate.get("overfit_risk") or oos.get("overfit_risk") or "not evaluated"
    return {
        "title": "Overfit diagnostic",
        "overfit_risk": overfit,
        "overfit_penalty": candidate.get("overfit_penalty", 0.0),
        "oos_metrics": oos,
        "forecast_uncertainty": candidate.get("forecast_uncertainty"),
        "caveat": "OOS diagnostics are historical validation checks, not predictions.",
    }
