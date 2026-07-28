from __future__ import annotations

from typing import Any


def build_report_sidebar(reports: list[dict[str, Any]] | None = None, *, selected_report_id: str | None = None) -> dict[str, Any]:
    items = []
    for report in reports or []:
        rid = report.get("report_id")
        items.append(
            {
                "report_id": rid,
                "title": report.get("title", "Untitled report"),
                "report_type": report.get("report_type", "unknown"),
                "generated_at": report.get("generated_at", ""),
                "review_status": report.get("report_review_status") or ("archived" if report.get("archived") else "unread"),
                "data_confidence": report.get("data_confidence", "unknown"),
                "selected": rid == selected_report_id,
                "research_only": True,
            }
        )
    return {"title": "Report list", "items": items, "selected_report_id": selected_report_id or (items[0]["report_id"] if items else ""), "empty": len(items) == 0, "research_only": True}
