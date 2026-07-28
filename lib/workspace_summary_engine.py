from __future__ import annotations

from pathlib import Path
from typing import Any

from .workspace_profile import get_or_create_workspace_profile
from .workspace_store import get_workspace_counts, list_recent_rows

RESEARCH_ONLY_NOTICE = "This workspace is for research and monitoring only. It does not provide financial advice, market-direction guidance, or execution instructions."


def build_workspace_summary(db_path: str | Path | None = None) -> dict[str, Any]:
    profile = get_or_create_workspace_profile(db_path)
    counts = get_workspace_counts(db_path)
    return {
        "profile": profile,
        "counts": counts,
        "notice": RESEARCH_ONLY_NOTICE,
        "provider_health_snapshot": {"status": "unknown" if counts["provider_snapshots"] == 0 else "recorded", "count": counts["provider_snapshots"]},
        "data_quality_snapshot": {"status": "unknown" if counts["data_quality_snapshots"] == 0 else "recorded", "count": counts["data_quality_snapshots"]},
        "recent_reports": list_recent_rows("report_inbox_items", 5, db_path),
        "recent_strategy_commits": list_recent_rows("strategy_commits", 5, db_path),
        "recent_alert_events": list_recent_rows("alert_events", 5, db_path),
        "recent_activity": list_recent_rows("workspace_activity_log", 10, db_path),
    }


def build_workspace_summary_cards(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    summary = build_workspace_summary(db_path)
    counts = summary["counts"]
    return [
        {"title": "Watchlist", "value": counts["watchlist_items"], "summary": "Active assets, regions, providers, strategies, and report topics being tracked.", "freshness": "local"},
        {"title": "Active Alert Rules", "value": counts["active_alert_rules"], "summary": "Manual/button-triggered research alert conditions.", "freshness": "local"},
        {"title": "Report Inbox", "value": counts["reports"], "summary": "Generated research reports with source snapshots and provider caveats.", "freshness": "local"},
        {"title": "Strategy Commits", "value": counts["strategy_commits"], "summary": "Research records for strategy candidates and guard results.", "freshness": "local"},
    ]

