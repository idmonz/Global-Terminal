from __future__ import annotations

from typing import Any


CHANGE_COLORS = {
    "strong positive": "#16a34a",
    "positive": "#4ade80",
    "neutral": "#334155",
    "negative": "#fb7185",
    "strong negative": "#dc2626",
}

RISK_COLORS = {
    "neutral": "#1e293b",
    "elevated risk": "#f59e0b",
    "severe risk": "#ef4444",
}

DATA_QUALITY_COLORS = {
    "fresh": "#22c55e",
    "stale": "#f59e0b",
    "missing": "#ef4444",
    "proxy": "#38bdf8",
    "historical-only": "#a78bfa",
    "key required": "#fb7185",
}


def clamp_heatmap_color_value(value: Any, *, lower: float = -10.0, upper: float = 10.0) -> float:
    try:
        number = float(value)
    except Exception:
        return 0.0
    return max(lower, min(upper, number))


def classify_heatmap_color_bucket(value: Any = None, *, mode: str = "daily_change", status: str | None = None) -> str:
    normalized_status = str(status or "").lower().replace("_", "-")
    if normalized_status in {"missing", "missing-key", "unavailable"}:
        return "missing" if normalized_status != "missing-key" else "key required"
    if normalized_status in {"proxy", "estimated", "historical-only", "stale"}:
        return normalized_status
    risk_mode = any(token in str(mode).lower() for token in ["risk", "quality", "health", "freshness", "severity", "stress"])
    number = clamp_heatmap_color_value(value, lower=0 if risk_mode else -10, upper=100 if risk_mode else 10)
    if risk_mode:
        if number >= 75:
            return "severe risk"
        if number >= 50:
            return "elevated risk"
        return "neutral"
    if number >= 3:
        return "strong positive"
    if number > 0.25:
        return "positive"
    if number <= -3:
        return "strong negative"
    if number < -0.25:
        return "negative"
    return "neutral"


def build_change_color_scale() -> list[tuple[float, str]]:
    return [(0.0, CHANGE_COLORS["strong negative"]), (0.35, CHANGE_COLORS["negative"]), (0.5, CHANGE_COLORS["neutral"]), (0.65, CHANGE_COLORS["positive"]), (1.0, CHANGE_COLORS["strong positive"])]


def build_risk_color_scale() -> list[tuple[float, str]]:
    return [(0.0, "#164e63"), (0.5, RISK_COLORS["elevated risk"]), (1.0, RISK_COLORS["severe risk"])]


def build_data_quality_color_scale() -> dict[str, str]:
    return dict(DATA_QUALITY_COLORS)


def build_provider_health_color_scale() -> dict[str, str]:
    return {"available": "#22c55e", "degraded": "#f59e0b", "missing_key": "#fb7185", "historical_only": "#a78bfa", "unavailable": "#94a3b8"}


def build_volatility_color_scale() -> list[tuple[float, str]]:
    return [(0.0, "#0f766e"), (0.45, "#f59e0b"), (0.75, "#fb7185"), (1.0, "#ef4444")]


def build_event_severity_color_scale() -> dict[str, str]:
    return {"low": "#22c55e", "watch": "#38bdf8", "medium": "#f59e0b", "high": "#fb7185", "critical": "#ef4444"}


def color_for_bucket(bucket: str) -> str:
    return {**CHANGE_COLORS, **RISK_COLORS, **DATA_QUALITY_COLORS}.get(str(bucket), "#64748b")
