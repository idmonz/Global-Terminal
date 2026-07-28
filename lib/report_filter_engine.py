from __future__ import annotations

from typing import Any

REPORT_REVIEW_STATES = ["unread", "reviewed", "archived", "requires_review"]


def build_report_filter_state(
    reports: list[dict[str, Any]] | None = None,
    *,
    query: str = "",
    report_type: str | None = None,
    review_status: str | None = None,
) -> dict[str, Any]:
    rows = list(reports or [])
    types = sorted({str(r.get("report_type") or "unknown") for r in rows})
    q = str(query or "").lower().strip()
    if q:
        rows = [r for r in rows if q in str(r.get("title", "")).lower() or q in str(r.get("summary", "")).lower()]
    if report_type and report_type != "all":
        rows = [r for r in rows if str(r.get("report_type")) == report_type]
    if review_status and review_status != "all":
        rows = [r for r in rows if str(r.get("report_review_status") or "unread") == review_status]
    return {
        "query": query,
        "selected_type": report_type or "all",
        "selected_review_status": review_status or "all",
        "available_types": ["all"] + types,
        "review_states": ["all"] + REPORT_REVIEW_STATES,
        "filtered_reports": rows,
        "count": len(rows),
        "research_only": True,
    }
