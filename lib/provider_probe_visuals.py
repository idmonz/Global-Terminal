from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .provider_health_engine import build_provider_health_summary


def build_provider_probe_table(results: list[dict[str, Any]] | None = None):
    rows = results or []
    return pd.DataFrame(rows) if pd is not None else rows


def build_provider_probe_metric_cards(results: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    summary = build_provider_health_summary(results or [])
    return [
        {"label": "Provider Score", "value": summary["score"], "delta": summary["label"], "freshness": "estimated"},
        {"label": "Ready", "value": summary["ready_count"], "delta": "providers", "freshness": "fresh"},
        {"label": "Gaps", "value": summary["gap_count"], "delta": "nonfatal", "freshness": "missing" if summary["gap_count"] else "fresh"},
        {"label": "Historical", "value": summary["historical_only_count"], "delta": "labeled", "freshness": "estimated"},
    ]


def build_provider_probe_badges(result: dict[str, Any]) -> list[str]:
    return [str(result.get("provider_id", "provider")), str(result.get("status", "unknown")), str(result.get("source_type", "source"))]


def build_provider_probe_cards(results: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    cards = []
    for result in results or []:
        cards.append(
            {
                "title": str(result.get("provider")),
                "summary": str(result.get("warning") or f"Status: {result.get('status', 'unknown')}."),
                "severity": "watch" if result.get("status") in {"missing_key", "historical_only"} else "low",
                "tags": build_provider_probe_badges(result),
                "freshness": "estimated",
            }
        )
    return cards
