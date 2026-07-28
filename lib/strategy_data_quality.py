from __future__ import annotations

from typing import Any


def compute_factor_coverage_score(factors: dict[str, Any] | None = None) -> float:
    if not factors:
        return 0.0
    total = len(factors)
    available = sum(1 for value in factors.values() if value is not None)
    return round(available / max(1, total) * 100, 1)


def compute_backtest_reliability_score(sample_length: int = 0, missing_pct: float = 0.0, oos_available: bool = False) -> float:
    length_score = min(100.0, sample_length / 756 * 100)
    missing_penalty = max(0.0, min(100.0, missing_pct))
    oos_bonus = 10.0 if oos_available else 0.0
    return round(max(0.0, min(100.0, length_score - missing_penalty + oos_bonus)), 1)


def compute_strategy_data_quality_score(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    factor_score = compute_factor_coverage_score(payload.get("factors"))
    reliability = compute_backtest_reliability_score(int(payload.get("sample_length", 0) or 0), float(payload.get("missing_pct", 0) or 0), bool(payload.get("oos_available", False)))
    source_confidence = float(payload.get("source_confidence", 50) or 50)
    proxy_penalty = 15.0 if payload.get("proxy_dependence") else 0.0
    score = round(max(0.0, min(100.0, factor_score * 0.3 + reliability * 0.4 + source_confidence * 0.3 - proxy_penalty)), 1)
    return {"score": score, "factor_coverage_score": factor_score, "backtest_reliability_score": reliability, "source_confidence": source_confidence, "label": "strong" if score >= 75 else "usable" if score >= 50 else "limited"}


def detect_strategy_data_gaps(payload: dict[str, Any] | None = None) -> list[str]:
    payload = payload or {}
    gaps = []
    if payload.get("sample_length", 0) < 252:
        gaps.append("Sample length below one trading year.")
    if payload.get("missing_pct", 0) > 5:
        gaps.append("Missing values exceed 5 percent.")
    if payload.get("proxy_dependence"):
        gaps.append("Proxy dependence is present.")
    if not payload.get("oos_available"):
        gaps.append("OOS validation is not available.")
    return gaps


def build_strategy_data_quality_cards(payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    score = compute_strategy_data_quality_score(payload)
    gaps = detect_strategy_data_gaps(payload)
    return [
        {"title": "Strategy Data Quality", "summary": f"Score {score['score']} marked {score['label']}.", "severity": "low" if score["score"] >= 75 else "watch", "tags": ["data quality"]},
        {"title": "Strategy Data Gaps", "summary": "; ".join(gaps or ["No major data gaps supplied."]), "severity": "medium" if gaps else "low", "tags": ["data gap"]},
    ]
