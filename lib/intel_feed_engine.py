from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .event_severity_badges import build_event_risk_label as _risk_label
from .osint_locate_actions import build_locate_action_payload
from .source_freshness_strip import build_source_freshness_strip


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def build_event_time_window_filter(events: list[dict[str, Any]] | None = None, *, hours: int = 24, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    rows = []
    for event in events or []:
        ts = _parse_time(event.get("created_at") or event.get("timestamp") or event.get("date"))
        if ts is None or ts >= cutoff:
            rows.append(event)
    return {"hours": hours, "events": rows, "count": len(rows), "research_only": True}


def build_event_risk_label(severity: str | int | float | None = None, *, confidence: str = "unknown") -> str:
    return _risk_label(severity, confidence=confidence)


def build_intel_feed(events: list[dict[str, Any]] | None = None, *, hours: int = 24, source_snapshot: Any = None, now: datetime | None = None) -> dict[str, Any]:
    # Keep the low-level feed builder deterministic by default.
    # Time-window filtering is still available through build_event_time_window_filter()
    # and the higher-level intel workflow.  Using wall-clock time here made archived
    # supplied events disappear as the calendar advanced, which broke reproducible
    # research reports and regression tests.
    if now is None:
        filtered = {"hours": hours, "events": list(events or []), "count": len(events or []), "research_only": True}
    else:
        filtered = build_event_time_window_filter(events or [], hours=hours, now=now)
    rows = []
    for event in filtered["events"]:
        confidence = event.get("confidence", "unknown")
        low_confidence = str(confidence).lower() in {"low", "low-confidence"}
        rows.append(
            {
                "title": event.get("title") or event.get("headline") or event.get("message") or "Untitled event",
                "summary": event.get("summary") or event.get("description") or "",
                "source": event.get("source") or "unknown",
                "time": event.get("created_at") or event.get("timestamp") or event.get("date") or "",
                "region": event.get("region") or event.get("location") or "Unspecified",
                "risk_label": build_event_risk_label(event.get("severity") or event.get("risk"), confidence=confidence),
                "confidence": confidence,
                "status_label": "unconfirmed" if low_confidence else "source-labeled",
                "locate_action": build_locate_action_payload(event),
                "research_only": True,
            }
        )
    return {
        "title": "Intel Feed",
        "rows": rows,
        "empty": len(rows) == 0,
        "empty_message": "Awaiting supplied intelligence context.",
        "source_freshness": build_source_freshness_strip(source_snapshot or [{"source": "intel_feed", "freshness": "unavailable", "confidence": "unknown"}], title="Intel feed source freshness"),
        "no_fake_live_data": True,
        "research_only": True,
    }
