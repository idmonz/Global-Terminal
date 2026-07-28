from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from .refresh_state import classify_refresh_state
from .visual_tokens import status_badge_tokens


def classify_source_freshness(timestamp: Any = None, *, stale_after_seconds: int = 900, now: datetime | None = None) -> str:
    return classify_refresh_state(timestamp, ttl_seconds=stale_after_seconds, now=now)


def build_data_truth_label(*, live: bool = False, proxy: bool = False, estimated: bool = False, historical_only: bool = False, missing_key: bool = False, unavailable: bool = False) -> str:
    if unavailable:
        return "unavailable"
    if missing_key:
        return "missing-key"
    if historical_only:
        return "historical-only"
    if proxy:
        return "proxy"
    if estimated:
        return "estimated"
    if live:
        return "live"
    return "unknown"


def build_source_freshness_indicator(
    source: str,
    *,
    timestamp: Any = None,
    status: str | None = None,
    stale_after_seconds: int = 900,
    confidence: float | int | None = None,
    truth_label: str | None = None,
) -> dict[str, Any]:
    freshness = status or classify_source_freshness(timestamp, stale_after_seconds=stale_after_seconds)
    tone = status_badge_tokens(freshness)
    return {
        "source": source,
        "freshness": freshness,
        "timestamp": timestamp,
        "confidence": confidence,
        "truth_label": truth_label or freshness,
        "color": tone["color"],
        "tooltip": f"{source}: {freshness}; confidence {confidence if confidence is not None else 'unknown'}; label {truth_label or freshness}.",
    }


def build_source_freshness_table(rows: Iterable[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    table = []
    for row in rows or []:
        table.append(
            build_source_freshness_indicator(
                str(row.get("source") or row.get("provider") or "source"),
                timestamp=row.get("timestamp") or row.get("checked_at") or row.get("published_at"),
                status=row.get("freshness") or row.get("status"),
                confidence=row.get("confidence"),
                truth_label=row.get("truth_label") or row.get("source_type"),
            )
        )
    return table
