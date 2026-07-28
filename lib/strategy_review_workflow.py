from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_workspace_db import execute_query, json_dumps, json_loads, utc_now
from .strategy_decision_log import get_strategy_commit

STRATEGY_REVIEW_STATES = ["draft", "reviewed", "requires_review", "archived"]


def update_strategy_review_status(
    commit_id: str,
    status: str,
    *,
    note: str = "",
    attach_report: str | None = None,
    attach_watchlist_item: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    commit = get_strategy_commit(commit_id, db_path)
    if not commit:
        return {"ok": False, "error": "commit_not_found", "research_only": True}
    target = str(status or "").lower()
    if target not in STRATEGY_REVIEW_STATES:
        return {"ok": False, "error": "invalid_status", "research_only": True}
    reports = list(commit.get("linked_reports", []))
    watch_items = list(commit.get("linked_watchlist_items", []))
    if attach_report and attach_report not in reports:
        reports.append(attach_report)
    if attach_watchlist_item and attach_watchlist_item not in watch_items:
        watch_items.append(attach_watchlist_item)
    archived = 1 if target == "archived" else 0
    reviewed_at = utc_now() if target == "reviewed" else commit.get("reviewed_at") or None
    execute_query(
        "UPDATE strategy_commits SET review_status = ?, reviewed_at = ?, review_notes = ?, archived = ?, linked_reports = ?, linked_watchlist_items = ? WHERE commit_id = ?",
        (target, reviewed_at, note or commit.get("review_notes") or "", archived, json_dumps(reports), json_dumps(watch_items), commit_id),
        db_path=db_path,
    )
    return {"ok": True, "commit_id": commit_id, "to": target, "linked_reports": reports, "linked_watchlist_items": watch_items, "research_only": True}


def build_strategy_review_workflow(commit: dict[str, Any] | None = None) -> dict[str, Any]:
    current = (commit or {}).get("review_status") or ("archived" if (commit or {}).get("archived") else "requires_review")
    actions = [
        {"label": "Mark reviewed", "status": "reviewed"},
        {"label": "Flag for review", "status": "requires_review"},
        {"label": "Archive", "status": "archived"},
        {"label": "Attach report", "status": current},
        {"label": "Attach watchlist item", "status": current},
        {"label": "Add review note", "status": current},
    ]
    return {
        "commit_id": (commit or {}).get("commit_id", ""),
        "current_status": current,
        "actions": [{**a, "research_only": True} for a in actions],
        "review_notes": (commit or {}).get("review_notes", ""),
        "reviewed_at": (commit or {}).get("reviewed_at", ""),
        "research_only": True,
    }
