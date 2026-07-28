from __future__ import annotations

from typing import Any


def build_strategy_commit_graph_table(commits: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [
        {
            "commit_id": commit.get("commit_id"),
            "parent_commit_id": commit.get("parent_commit_id") or "root",
            "strategy_id": commit.get("strategy_id"),
            "created_at": commit.get("created_at"),
            "status": commit.get("review_status") or commit.get("status") or "draft",
            "linked_reports": len(commit.get("linked_reports", []) or []),
            "linked_watchlist_items": len(commit.get("linked_watchlist_items", []) or []),
            "research_only": True,
        }
        for commit in commits or []
    ]
