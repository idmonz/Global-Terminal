from __future__ import annotations

from typing import Any


def kalman_lite_level_trend(series: list[float], *, alpha: float = 0.35, beta: float = 0.10) -> dict[str, Any]:
    values = [float(x) for x in series]
    if len(values) < 2:
        return {"ok": False, "error": "insufficient_observations", "research_only": True}
    level = values[0]
    trend = values[1] - values[0]
    states = []
    for value in values:
        prev_level = level
        level = alpha * value + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
        states.append({"level": level, "trend": trend})
    residuals = [v - s["level"] for v, s in zip(values, states)]
    uncertainty = sum(abs(r) for r in residuals) / len(residuals)
    return {"ok": True, "states": states, "last_level": level, "last_trend": trend, "state_uncertainty_proxy": uncertainty, "caveat": "local smoother state only; no forecast claim", "research_only": True}
