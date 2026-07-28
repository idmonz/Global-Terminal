from __future__ import annotations
from pathlib import Path
from typing import Any
from .provider_report_memory import build_provider_report_memory, build_data_quality_report_memory


def build_report_source_snapshot(context: dict[str, Any] | None = None, *, db_path: str | Path | None = None) -> dict[str, Any]:
    context = context or {}
    provider = build_provider_report_memory(db_path=db_path)
    dq = build_data_quality_report_memory(db_path=db_path)
    labels = ["manual-trigger", "research-only"]
    if provider.get("status") in {"stale", "missing_key", "error", "unavailable"}:
        labels.append("provider-caveat")
    if dq.get("status") in {"stale", "proxy", "missing", "unavailable"}:
        labels.append("data-quality-caveat")
    return {"freshness": context.get("freshness", "local"), "confidence": context.get("confidence", "available-data"), "labels": labels, "provider_memory_status": provider.get("status"), "data_quality_status": dq.get("status"), "provider_gap_count": provider.get("gap_count", 0), "data_gap_count": dq.get("gap_count", 0)}


def build_provider_gap_lines(provider_memory: dict[str, Any], dq_memory: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for row in provider_memory.get("gaps", [])[:10]:
        lines.append(f"- Provider `{row.get('provider_name')}` status `{row.get('status')}` freshness `{row.get('freshness')}` missing keys `{row.get('missing_keys', [])}`")
    for row in dq_memory.get("gaps", [])[:10]:
        lines.append(f"- Data quality scope `{row.get('scope')}` status `{row.get('status')}` freshness `{row.get('freshness')}` gaps `{row.get('gaps_json', [])}`")
    return lines or ["- No stored provider/data quality gaps supplied."]
