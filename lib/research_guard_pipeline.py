from __future__ import annotations
from typing import Any
from .strategy_guard_rules import (
    GUARD_FUNCTIONS, build_guard_result,
    data_quality_guard, sample_length_guard, missing_data_guard, proxy_dependence_guard,
    source_freshness_guard, overfit_guard, lookahead_bias_guard, survivorship_bias_guard,
    turnover_guard, drawdown_guard, concentration_guard, leverage_guard,
    no_recommendation_language_guard as _no_recommendation_language_guard,
)


def no_recommendation_language_guard(payload: dict[str, Any] | str | None = None, text: str = "") -> dict[str, Any]:
    if isinstance(payload, str) and not text:
        text = payload
        payload = {}
    return _no_recommendation_language_guard(payload or {}, text)

def run_research_guard_pipeline(payload: dict[str, Any] | None = None, text: str = "") -> list[dict[str, Any]]:
    payload = payload or {}
    return [fn(payload, text) for fn in GUARD_FUNCTIONS]


def summarize_guard_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in results or []:
        counts[row.get("status", "unknown")] = counts.get(row.get("status", "unknown"), 0) + 1
    review_count = counts.get("warning", 0) + counts.get("failed", 0) + counts.get("skipped_no_data", 0)
    return {"counts": counts, "requires_review": bool(review_count), "review_count": review_count, "guard_count": len(results or [])}


def build_guard_cards(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"title": r.get("guard"), "summary": r.get("message"), "severity": r.get("severity", "watch"), "status": r.get("status")} for r in results or []]

__all__ = [
    "run_research_guard_pipeline", "build_guard_result", "summarize_guard_results", "build_guard_cards",
    "data_quality_guard", "sample_length_guard", "missing_data_guard", "proxy_dependence_guard",
    "source_freshness_guard", "overfit_guard", "lookahead_bias_guard", "survivorship_bias_guard",
    "turnover_guard", "drawdown_guard", "concentration_guard", "leverage_guard", "no_recommendation_language_guard",
]
