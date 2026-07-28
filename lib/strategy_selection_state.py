from __future__ import annotations

from pathlib import Path
from typing import Any, MutableMapping

from .research_session_state import get_research_session_state, set_session_selection
from .strategy_decision_log import get_strategy_commit, list_strategy_commits


def select_strategy_commit(commit_id: str | None = None, *, db_path: str | Path | None = None, session_state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    state = get_research_session_state(session_state)
    commits = list_strategy_commits(include_archived=True, db_path=db_path)
    selected_id = commit_id or state.get("selected_strategy_commit_id") or state.get("selected_commit_id") or (commits[0]["commit_id"] if commits else "")
    selected = get_strategy_commit(selected_id, db_path) if selected_id else None
    if not selected and commits:
        selected_id = commits[0]["commit_id"]
        selected = get_strategy_commit(selected_id, db_path)
    if selected:
        set_session_selection(state, "selected_strategy_commit_id", selected_id)
    return {"selected_commit_id": selected_id if selected else "", "selected_strategy_commit_id": selected_id if selected else "", "selected_commit": selected, "available_count": len(commits), "research_only": True}
