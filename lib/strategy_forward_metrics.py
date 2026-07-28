from __future__ import annotations
from typing import Any
from .research_workspace_db import utc_now


def build_forward_tracking_snapshot(commit: dict[str, Any], evaluation: dict[str, Any] | None = None) -> dict[str, Any]:
    evaluation = evaluation or {}
    return {"commit_id": commit.get("commit_id"), "strategy_id": commit.get("strategy_id"), "tracked_at": utc_now(), "tracking_status": evaluation.get("tracking_status", "pending_manual_review"), "outcome_note": evaluation.get("outcome_note", "No subsequent evaluation supplied."), "metrics": evaluation.get("metrics", {})}


def update_forward_tracking(commit: dict[str, Any], evaluation: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_forward_tracking_snapshot(commit, evaluation)
