from __future__ import annotations

from typing import Any

from .strategy_decision_log import compare_strategy_commits


def build_strategy_commit_diff_panel(left_commit: dict[str, Any] | None = None, right_commit: dict[str, Any] | None = None) -> dict[str, Any]:
    if not left_commit or not right_commit:
        return {"title": "Commit diff", "empty": True, "message": "Select two commits to compare research snapshots.", "research_only": True}
    return {
        "title": "Commit diff",
        "left_commit_id": left_commit.get("commit_id"),
        "right_commit_id": right_commit.get("commit_id"),
        "changed_fields": [key for key in sorted(set(left_commit) | set(right_commit)) if left_commit.get(key) != right_commit.get(key)],
        "research_only": True,
    }


def build_strategy_commit_diff_from_ids(left_commit_id: str, right_commit_id: str, db_path=None) -> dict[str, Any]:
    return {"title": "Commit diff", "diff": compare_strategy_commits(left_commit_id, right_commit_id, db_path), "research_only": True}
