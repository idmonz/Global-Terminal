from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, MutableMapping

from .report_inbox import get_report, list_reports
from .report_reader_panel import build_report_reader_panel
from .report_review_workflow import build_report_review_workflow, update_report_review_status
from .report_source_caveat_panel import build_report_source_caveat_panel
from .research_session_state import get_research_session_state, persist_report_filter_state, persist_last_action_result, set_session_selection


def _filter_reports(reports: list[dict[str, Any]], *, report_type: str | None = None, review_status: str | None = None, query: str = "") -> list[dict[str, Any]]:
    rows = reports
    if report_type and report_type != "all":
        rows = [r for r in rows if r.get("report_type") == report_type]
    if review_status and review_status != "all":
        rows = [r for r in rows if (r.get("report_review_status") or "unread") == review_status]
    if query:
        needle = query.lower()
        rows = [r for r in rows if needle in str(r.get("title", "")).lower() or needle in str(r.get("summary", "")).lower()]
    return rows


def build_report_reader_workflow_state(
    *,
    selected_report_id: str | None = None,
    report_type: str | None = None,
    review_status: str | None = None,
    query: str = "",
    db_path: str | Path | None = None,
    session_state: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = get_research_session_state(session_state)
    existing_filters = dict(state.get("report_filters") or {})
    report_type = report_type if report_type is not None else existing_filters.get("report_type", "all")
    review_status = review_status if review_status is not None else existing_filters.get("review_status", "all")
    query = query if query is not None else existing_filters.get("query", "")
    persist_report_filter_state(report_type=report_type or "all", review_status=review_status or "all", query=query or "", session_state=state)
    reports = list_reports(include_archived=True, db_path=db_path)
    filtered = _filter_reports(reports, report_type=report_type, review_status=review_status, query=query)
    selected_id = selected_report_id or state.get("selected_report_id") or (filtered[0]["report_id"] if filtered else "")
    selected = get_report(selected_id, db_path) if selected_id else None
    if selected and selected not in filtered and (report_type or review_status or query):
        selected = filtered[0] if filtered else None
        selected_id = selected["report_id"] if selected else ""
    if selected_id:
        set_session_selection(state, "selected_report_id", selected_id)
    return {
        "selected_report_id": selected_id,
        "filters": {"report_type": report_type or "all", "review_status": review_status or "all", "query": query},
        "sidebar": {
            "selected_report_id": selected_id,
            "items": [
                {
                    "report_id": r["report_id"],
                    "title": r.get("title", "Untitled"),
                    "report_type": r.get("report_type"),
                    "review_status": r.get("report_review_status", "unread"),
                    "selected": r["report_id"] == selected_id,
                    "research_only": True,
                }
                for r in filtered
            ],
        },
        "selected_report": selected,
        "reader": build_report_reader_panel(selected) if selected else {"empty": True, "message": "No selected report", "research_only": True},
        "review_workflow": build_report_review_workflow(selected),
        "source_caveat_panel": build_report_source_caveat_panel(selected) if selected else {"empty": True, "research_only": True},
        "linked_context": build_report_linked_context_panel(selected),
        "export_payload": build_selected_report_export_payload(selected),
        "research_only": True,
    }


def update_selected_report_review(report_id: str, status: str, *, notes: str = "", db_path: str | Path | None = None, session_state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    state = get_research_session_state(session_state)
    result = update_report_review_status(report_id, status, notes=notes, db_path=db_path)
    if result.get("ok"):
        set_session_selection(state, "selected_report_id", report_id)
        persist_last_action_result({"action": "UPDATE_REPORT_REVIEW_STATUS", "report_id": report_id, "status": status, "ok": True, "research_only": True}, session_state=state)
        filters = dict(state.get("report_filters") or {})
        result["workflow_state"] = build_report_reader_workflow_state(selected_report_id=report_id, report_type=filters.get("report_type"), review_status=filters.get("review_status"), query=filters.get("query", ""), db_path=db_path, session_state=state)
    else:
        result["workflow_state"] = {}
    return result


def build_report_linked_context_panel(report: dict[str, Any] | None) -> dict[str, Any]:
    report = report or {}
    return {
        "title": "Linked context",
        "watchlist_items": report.get("linked_watchlist_items", []),
        "events": report.get("linked_events", []),
        "strategy_commits": report.get("linked_strategy_commits", []),
        "assets": report.get("linked_assets", []),
        "regions": report.get("linked_regions", []),
        "research_only": True,
    }


def build_selected_report_export_payload(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {"empty": True, "research_only": True}
    return {
        "report_id": report.get("report_id"),
        "filename": f"report_{report.get('report_id')}.md",
        "markdown_body": report.get("markdown_body", ""),
        "html_preview_safe": escape(report.get("html_body_optional", "")),
        "research_only": True,
    }
