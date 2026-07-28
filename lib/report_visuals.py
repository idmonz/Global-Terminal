from __future__ import annotations
from typing import Any


def build_report_cards(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"title": r.get("title"), "summary": r.get("summary"), "report_type": r.get("report_type"), "data_confidence": r.get("data_confidence"), "generated_at": r.get("generated_at")} for r in reports]


def build_report_timeline(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(reports, key=lambda r: str(r.get("generated_at", "")), reverse=True)

