from __future__ import annotations
from pathlib import Path
from typing import Any
from .research_workspace_db import execute_query, utc_now
from .strategy_decision_log import get_strategy_commit


def build_forward_tracking_snapshot(commit: dict[str, Any], observations: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"commit_id": commit.get("commit_id"), "strategy_id": commit.get("strategy_id"), "observations": observations or {}, "created_at": utc_now(), "research_only": True}


def update_forward_tracking(commit_id: str, observations: dict[str, Any] | None = None, db_path: str | Path | None = None) -> dict[str, Any] | None:
    commit = get_strategy_commit(commit_id, db_path)
    if not commit: return None
    if not commit.get("forward_tracking_start"):
        execute_query("UPDATE strategy_commits SET forward_tracking_start = ?, status = ? WHERE commit_id = ?", (utc_now(), "tracked", commit_id), db_path=db_path)
        commit = get_strategy_commit(commit_id, db_path)
    return build_forward_tracking_snapshot(commit or {}, observations)

