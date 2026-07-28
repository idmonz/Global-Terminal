from __future__ import annotations
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from .alert_store import list_alert_events
from .watchlist_engine import build_watchlist_context
from .strategy_decision_log import list_strategy_commits
from .provider_report_memory import build_provider_report_memory, build_data_quality_report_memory
from .report_source_snapshots import build_report_source_snapshot as _build_report_source_snapshot


def build_report_context(report_type: str = "Watchlist Brief", db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]:
    supplied_context = extra.get("supplied_context") or extra
    watchlist = build_watchlist_context(db_path, supplied_context=supplied_context)
    context = {
        "report_type": report_type,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "watchlist": watchlist,
        "linked_events": watchlist.get("bundle", {}).get("events", {}).get("matches", []),
        "alert_events": list_alert_events(limit=50, db_path=db_path),
        "strategy_commits": list_strategy_commits(db_path=db_path),
        "provider_memory": build_provider_report_memory(db_path=db_path),
        "data_quality_memory": build_data_quality_report_memory(db_path=db_path),
        "provider_gaps": [],
        "research_only": True,
        "db_path": str(db_path) if db_path else None,
    }
    context["source_snapshot"] = _build_report_source_snapshot(context, db_path=db_path)
    context["provider_gaps"] = context["provider_memory"].get("gaps", []) + context["data_quality_memory"].get("gaps", [])
    context.update(extra)
    return context


def build_report_source_snapshot_compat(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("source_snapshot") or {"freshness": "unknown", "confidence": "unknown", "labels": ["unavailable"]}

# Backward-compatible public name used by Goal 11 code.
def build_report_source_snapshot(context: dict[str, Any]) -> dict[str, Any]:  # type: ignore[override]
    return context.get("source_snapshot") or {"freshness": "unknown", "confidence": "unknown", "labels": ["unavailable"]}
