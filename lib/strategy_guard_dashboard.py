from __future__ import annotations

from typing import Any

from .research_guard_pipeline import summarize_guard_results


def build_strategy_guard_dashboard(commits: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    cards = []
    aggregate = {"warning": 0, "failed": 0, "passed": 0, "skipped_no_data": 0}
    for commit in commits or []:
        summary = summarize_guard_results(commit.get("guard_results_json", []) or [])
        for key, value in summary.get("counts", {}).items():
            aggregate[key] = aggregate.get(key, 0) + int(value)
        cards.append({"commit_id": commit.get("commit_id"), "strategy_id": commit.get("strategy_id"), "summary": summary, "research_only": True})
    return {"title": "Guard dashboard", "aggregate": aggregate, "cards": cards, "requires_review_count": sum(1 for c in cards if c["summary"].get("requires_review")), "research_only": True}
