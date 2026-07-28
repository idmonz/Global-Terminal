from __future__ import annotations

from pathlib import Path
from typing import Any, MutableMapping

from .research_artifact_store import list_research_artifacts, store_research_artifact
from .strategy_commit_reader import build_strategy_commit_reader
from .strategy_decision_log import attach_report_to_commit, attach_watchlist_items_to_commit, compare_strategy_commits, get_strategy_commit, list_strategy_commits
from .strategy_guard_dashboard import build_strategy_guard_dashboard
from .strategy_review_workflow import build_strategy_review_workflow, update_strategy_review_status
from .research_session_state import get_research_session_state, persist_last_action_result, set_session_selection


def build_selected_strategy_payload(commit_id: str | None = None, *, compare_to_commit_id: str | None = None, db_path: str | Path | None = None, session_state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    state = get_research_session_state(session_state)
    commits = list_strategy_commits(include_archived=True, db_path=db_path)
    selected_id = commit_id or state.get("selected_strategy_commit_id") or state.get("selected_commit_id") or (commits[0]["commit_id"] if commits else "")
    selected = get_strategy_commit(selected_id, db_path) if selected_id else None
    if selected:
        set_session_selection(state, "selected_strategy_commit_id", selected_id)
    return {
        "selected_commit_id": selected_id if selected else "",
        "selected_strategy_commit_id": selected_id if selected else "",
        "selected_commit": selected,
        "review_queue": [
            {"commit_id": c["commit_id"], "strategy_id": c.get("strategy_id"), "review_status": c.get("review_status"), "selected": c["commit_id"] == selected_id, "research_only": True}
            for c in commits
        ],
        "commit_reader": build_strategy_commit_reader(selected) if selected else {"empty": True, "research_only": True},
        "review_workflow": build_strategy_review_workflow(selected),
        "diff_panel": build_selected_commit_diff(selected_id, compare_to_commit_id=compare_to_commit_id, db_path=db_path) if selected else {"empty": True, "research_only": True},
        "guard_dashboard": build_selected_commit_guard_dashboard(selected_id, db_path=db_path) if selected else {"empty": True, "research_only": True},
        "artifact_timeline": {"events": list_research_artifacts(selected_id, db_path=db_path) if selected else [], "research_only": True},
        "forward_tracking": {"commit_id": selected_id if selected else "", "linked": bool(selected), "research_only": True},
        "research_only": True,
    }


def update_selected_strategy_review(commit_id: str, status: str, *, note: str = "", db_path: str | Path | None = None, session_state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    state = get_research_session_state(session_state)
    result = update_strategy_review_status(commit_id, status, note=note, db_path=db_path)
    if result.get("ok"):
        set_session_selection(state, "selected_strategy_commit_id", commit_id)
        persist_last_action_result({"action": "UPDATE_STRATEGY_REVIEW_STATUS", "commit_id": commit_id, "status": status, "ok": True, "research_only": True}, session_state=state)
        result["workflow_state"] = build_selected_strategy_payload(commit_id, db_path=db_path, session_state=state)
    else:
        result["workflow_state"] = {}
    return result


def attach_artifact_to_selected_commit(commit_id: str, *, report_id: str | None = None, watchlist_item_id: str | None = None, note: str = "", db_path: str | Path | None = None) -> dict[str, Any]:
    if report_id:
        commit = attach_report_to_commit(commit_id, report_id, db_path=db_path)
        if not commit:
            return {"ok": False, "error": "commit_not_found", "research_only": True}
        artifact = store_research_artifact(commit_id, "report", f"Linked report {report_id}", payload={"report_id": report_id, "note": note}, db_path=db_path)
    elif watchlist_item_id:
        commit = attach_watchlist_items_to_commit(commit_id, [watchlist_item_id], db_path=db_path)
        if not commit:
            return {"ok": False, "error": "commit_not_found", "research_only": True}
        artifact = store_research_artifact(commit_id, "watchlist", f"Linked watchlist item {watchlist_item_id}", payload={"watchlist_item_id": watchlist_item_id, "note": note}, db_path=db_path)
    else:
        artifact = store_research_artifact(commit_id, "note", note or "Review note", payload={"note": note}, db_path=db_path)
    return {"ok": True, "commit_id": commit_id, "artifact": artifact, "timeline": list_research_artifacts(commit_id, db_path=db_path), "research_only": True}


def build_selected_commit_diff(commit_id: str, *, compare_to_commit_id: str | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
    commit = get_strategy_commit(commit_id, db_path)
    if not commit:
        return {"empty": True, "research_only": True}
    parent_id = compare_to_commit_id or commit.get("parent_commit_id")
    if not parent_id:
        return {"commit_id": commit_id, "comparison": "none", "changes": [], "research_only": True}
    diff = compare_strategy_commits(parent_id, commit_id, db_path=db_path)
    return {"commit_id": commit_id, "compare_to": parent_id, "diff": diff, "research_only": True}


def build_selected_commit_guard_dashboard(commit_id: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    commit = get_strategy_commit(commit_id, db_path)
    return build_strategy_guard_dashboard([commit]) if commit else {"empty": True, "research_only": True}
