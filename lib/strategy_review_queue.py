from __future__ import annotations
from typing import Any

REVIEW_STATES = {"draft", "reviewed", "tracked", "archived", "requires_review"}


def classify_commit_review_state(commit: dict[str, Any]) -> str:
    if commit.get("archived"):
        return "archived"
    if any(g.get("status") in {"warning", "failed", "skipped_no_data"} for g in commit.get("guard_results_json", []) or []):
        return "requires_review"
    return str(commit.get("status") or "draft")


def build_strategy_review_queue(commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank = {"requires_review": 5, "draft": 4, "tracked": 3, "reviewed": 2, "archived": 1}
    rows = [{**c, "review_state": classify_commit_review_state(c)} for c in commits or []]
    return sorted(rows, key=lambda c: (rank.get(c["review_state"], 0), c.get("created_at", "")), reverse=True)
