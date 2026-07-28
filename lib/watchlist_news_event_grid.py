from __future__ import annotations

from typing import Any

from .event_severity_badges import build_event_severity_badge


def _event_key(event: dict[str, Any]) -> tuple[str, str, str]:
    return (str(event.get("title") or event.get("headline") or event.get("message") or "").lower(), str(event.get("source") or "").lower(), str(event.get("created_at") or event.get("timestamp") or event.get("date") or "")[:10])


def build_watchlist_news_event_grid(events: list[dict[str, Any]] | None = None, *, limit: int = 20) -> dict[str, Any]:
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict[str, Any]] = []
    for event in events or []:
        key = _event_key(event)
        if key in seen:
            continue
        seen.add(key)
        badge = build_event_severity_badge(event.get("severity") or event.get("risk"), confidence=event.get("confidence", "unknown"), source=event.get("source", ""))
        rows.append(
            {
                "title": event.get("title") or event.get("headline") or event.get("message") or "Untitled event",
                "source": event.get("source") or "unknown",
                "time": event.get("created_at") or event.get("timestamp") or event.get("date") or "",
                "risk_label": badge["label"],
                "confidence": event.get("confidence", "unknown"),
                "linked_item": event.get("watch_item_id") or event.get("symbol") or event.get("region") or "",
                "caveat": badge["caveat"],
                "research_only": True,
            }
        )
    return {
        "title": "Watchlist news / event grid",
        "rows": rows[:limit],
        "deduped_count": len(seen),
        "empty": not rows,
        "empty_message": "No supplied news or event context is available.",
        "no_fake_live_data": True,
        "research_only": True,
    }
