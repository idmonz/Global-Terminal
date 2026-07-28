from __future__ import annotations
from pathlib import Path
from typing import Any
from .strategy_decision_log import list_strategy_commits, build_strategy_commit_graph_payload, build_strategy_review_queue_payload
from .strategy_commit_visuals import build_strategy_commit_cards
from .research_guard_pipeline import build_guard_cards
from .strategy_review_workflow import build_strategy_review_workflow
from .strategy_artifact_timeline import build_strategy_artifact_timeline
from .strategy_commit_reader import build_strategy_commit_reader
from .strategy_guard_dashboard import build_strategy_guard_dashboard
from .strategy_commit_graph_table import build_strategy_commit_graph_table
from .strategy_commit_diff_panel import build_strategy_commit_diff_panel


def build_strategy_log_page_payload(db_path: str | Path | None = None) -> dict[str, Any]:
    commits = list_strategy_commits(db_path=db_path)
    latest = commits[0] if commits else None
    previous = commits[1] if len(commits) > 1 else None
    return {
        "commits": commits,
        "cards": build_strategy_commit_cards(commits),
        "graph": build_strategy_commit_graph_payload(commits),
        "graph_table": build_strategy_commit_graph_table(commits),
        "review_queue": build_strategy_review_queue_payload(commits),
        "review_workflow": build_strategy_review_workflow(latest),
        "commit_reader": build_strategy_commit_reader(latest),
        "guard_dashboard": build_strategy_guard_dashboard(commits),
        "artifact_timeline": build_strategy_artifact_timeline((latest or {}).get("commit_id"), db_path=db_path),
        "commit_diff_panel": build_strategy_commit_diff_panel(previous, latest) if previous and latest else build_strategy_commit_diff_panel(),
        "latest_guard_cards": build_guard_cards((latest or {}).get("guard_results_json", [])),
        "forward_tracking_panel": {"title": "Forward tracking", "latest_commit_id": (latest or {}).get("commit_id", ""), "status": (latest or {}).get("forward_tracking_start") or "not_started", "research_only": True},
        "linked_context": {"reports": (latest or {}).get("linked_reports", []), "watchlist_items": (latest or {}).get("linked_watchlist_items", [])},
        "empty_states": {"no_strategy_commits": len(commits) == 0},
        "raw_payload_available": True,
        "research_only": True,
    }
