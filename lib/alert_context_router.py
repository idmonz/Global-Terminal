from __future__ import annotations
from pathlib import Path
from typing import Any
from .alert_metric_resolver import resolve_alert_metric


def build_alert_data_context(rule: dict[str, Any], supplied_context: dict[str, Any] | None = None, *, db_path: str | Path | None = None) -> dict[str, Any]:
    return resolve_alert_metric(rule, supplied_context or {}, db_path=db_path)


def build_alert_evaluation_batch(rules: list[dict[str, Any]], supplied_context: dict[str, Any] | None = None, *, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    return [build_alert_data_context(rule, supplied_context, db_path=db_path) for rule in rules]


def build_alert_review_queue(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    severity_rank = {"critical": 5, "high": 4, "elevated": 3, "watch": 2, "info": 1}
    return sorted(events or [], key=lambda e: (severity_rank.get(str(e.get("severity")), 0), e.get("created_at", "")), reverse=True)
