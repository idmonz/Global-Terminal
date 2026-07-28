from __future__ import annotations

from typing import Any

RISK_LABELS = ["LOW", "ELEVATED", "HIGH", "CRITICAL"]
_SEVERITY_MAP = {
    "info": "LOW",
    "watch": "LOW",
    "low": "LOW",
    "elevated": "ELEVATED",
    "medium": "ELEVATED",
    "warning": "ELEVATED",
    "high": "HIGH",
    "severe": "HIGH",
    "critical": "CRITICAL",
    "emergency": "CRITICAL",
}


def build_event_risk_label(severity: str | int | float | None = None, *, confidence: str = "unknown") -> str:
    if isinstance(severity, (int, float)):
        if severity >= 90:
            return "CRITICAL"
        if severity >= 70:
            return "HIGH"
        if severity >= 40:
            return "ELEVATED"
        return "LOW"
    label = _SEVERITY_MAP.get(str(severity or "low").strip().lower(), "LOW")
    if str(confidence).lower() in {"low", "low-confidence"} and label in {"HIGH", "CRITICAL"}:
        return "ELEVATED"
    return label


def build_event_severity_badge(severity: str | int | float | None = None, *, confidence: str = "unknown", source: str = "") -> dict[str, Any]:
    label = build_event_risk_label(severity, confidence=confidence)
    return {
        "label": label,
        "severity": str(severity or "low"),
        "confidence": confidence or "unknown",
        "source": source or "",
        "caveat": "Low-confidence event: display as unconfirmed." if str(confidence).lower() in {"low", "low-confidence"} else "Review source context before escalation.",
        "research_only": True,
    }


def build_event_severity_badges(events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [build_event_severity_badge(e.get("severity") or e.get("risk"), confidence=e.get("confidence", "unknown"), source=e.get("source", "")) for e in events or []]
