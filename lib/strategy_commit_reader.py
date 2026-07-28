from __future__ import annotations

from typing import Any

from .research_guard_pipeline import build_guard_cards, summarize_guard_results
from .source_freshness_strip import build_source_freshness_strip


def build_strategy_commit_reader(commit: dict[str, Any] | None = None) -> dict[str, Any]:
    if not commit:
        return {"title": "No strategy commit selected", "empty": True, "message": "Create or select a research commit.", "research_only": True}
    guards = commit.get("guard_results_json", []) or []
    return {
        "commit_id": commit.get("commit_id"),
        "strategy_id": commit.get("strategy_id"),
        "message": commit.get("message", ""),
        "created_at": commit.get("created_at", ""),
        "review_status": commit.get("review_status") or commit.get("status") or "draft",
        "guard_summary": summarize_guard_results(guards),
        "guard_cards": build_guard_cards(guards),
        "source_freshness": build_source_freshness_strip(commit.get("provider_snapshot_json", {}), title="Commit provider freshness"),
        "linked_reports": commit.get("linked_reports", []),
        "linked_watchlist_items": commit.get("linked_watchlist_items", []),
        "raw_payload_available": True,
        "research_only": True,
    }
