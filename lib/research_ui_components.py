from __future__ import annotations

from typing import Any

from .research_card_deck import build_next_action_buttons, build_research_card_deck
from .research_empty_states import build_empty_state_panel
from .source_freshness_strip import build_provider_caveat_chips, build_source_freshness_strip
from .event_severity_badges import build_event_severity_badge
from .methodology_tooltip import build_methodology_tooltip_payload


def build_status_chip_row(items: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [
        {
            "label": item.get("label") or item.get("status") or "unknown",
            "value": item.get("value", ""),
            "status": item.get("status", "unknown"),
            "caveat": item.get("caveat", ""),
            "research_only": True,
        }
        for item in items or []
    ]


def build_compact_metric_row(metrics: list[dict[str, Any]] | dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if isinstance(metrics, dict):
        metrics = [{"label": key, "value": value} for key, value in metrics.items()]
    return [
        {
            "label": str(metric.get("label", "Metric")),
            "value": metric.get("value", "N/A"),
            "delta": metric.get("delta", ""),
            "status": metric.get("status", "neutral"),
            "source": metric.get("source", ""),
            "research_only": True,
        }
        for metric in metrics or []
    ]


__all__ = [
    "build_source_freshness_strip",
    "build_provider_caveat_chips",
    "build_event_severity_badge",
    "build_methodology_tooltip_payload",
    "build_research_card_deck",
    "build_empty_state_panel",
    "build_next_action_buttons",
    "build_status_chip_row",
    "build_compact_metric_row",
]
