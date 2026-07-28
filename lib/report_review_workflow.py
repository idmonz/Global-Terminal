from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_workspace_db import execute_query, utc_now
from .report_inbox import get_report

REPORT_REVIEW_TRANSITIONS = {
    "unread": {"reviewed", "requires_review", "archived"},
    "requires_review": {"reviewed", "archived"},
    "reviewed": {"requires_review", "archived"},
    "archived": {"requires_review", "reviewed"},
}


def update_report_review_status(report_id: str, status: str, *, notes: str = "", db_path: str | Path | None = None) -> dict[str, Any]:
    report = get_report(report_id, db_path)
    if not report:
        return {"ok": False, "error": "report_not_found", "research_only": True}
    current = report.get("report_review_status") or ("archived" if report.get("archived") else "unread")
    target = str(status or "").lower()
    if target not in {"unread", "reviewed", "archived", "requires_review"}:
        return {"ok": False, "error": "invalid_status", "current": current, "research_only": True}
    archived = 1 if target == "archived" else 0
    reviewed_at = utc_now() if target == "reviewed" else report.get("reviewed_at") or None
    execute_query(
        "UPDATE report_inbox_items SET report_review_status = ?, reviewed_at = ?, review_notes = ?, archived = ?, updated_at = ? WHERE report_id = ?",
        (target, reviewed_at, notes or report.get("review_notes") or "", archived, utc_now(), report_id),
        db_path=db_path,
    )
    return {"ok": True, "report_id": report_id, "from": current, "to": target, "research_only": True}


def build_report_review_workflow(report: dict[str, Any] | None = None) -> dict[str, Any]:
    current = (report or {}).get("report_review_status") or ("archived" if (report or {}).get("archived") else "unread")
    return {
        "current_status": current,
        "allowed_next": sorted(REPORT_REVIEW_TRANSITIONS.get(current, {"reviewed", "requires_review", "archived"})),
        "review_notes": (report or {}).get("review_notes", ""),
        "reviewed_at": (report or {}).get("reviewed_at", ""),
        "research_only": True,
    }
