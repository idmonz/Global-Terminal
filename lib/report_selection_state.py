from __future__ import annotations

from pathlib import Path
from typing import Any, MutableMapping

from .report_inbox import get_report, list_reports
from .research_session_state import get_research_session_state, set_session_selection


def select_report(report_id: str | None, *, db_path: str | Path | None = None, session_state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    state = get_research_session_state(session_state)
    reports = list_reports(include_archived=True, db_path=db_path)
    selected_id = report_id or state.get("selected_report_id") or (reports[0]["report_id"] if reports else "")
    selected = get_report(selected_id, db_path) if selected_id else None
    if not selected and reports:
        selected_id = reports[0]["report_id"]
        selected = get_report(selected_id, db_path)
    if selected:
        set_session_selection(state, "selected_report_id", selected_id)
    return {"selected_report_id": selected_id if selected else "", "selected_report": selected, "available_count": len(reports), "research_only": True}


def build_selected_report_payload(report_id: str | None = None, *, db_path: str | Path | None = None, session_state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    return select_report(report_id, db_path=db_path, session_state=session_state)
