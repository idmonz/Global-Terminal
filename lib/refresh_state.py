from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def classify_refresh_state(last_refreshed: Any = None, *, ttl_seconds: int = 300, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    last = _parse_time(last_refreshed)
    if last is None:
        return "unknown"
    age = max(0.0, (now - last).total_seconds())
    if age <= ttl_seconds:
        return "fresh"
    if age <= ttl_seconds * 3:
        return "aging"
    return "stale"


def should_refresh(last_refreshed: Any = None, *, ttl_seconds: int = 300, now: datetime | None = None) -> bool:
    return classify_refresh_state(last_refreshed, ttl_seconds=ttl_seconds, now=now) in {"unknown", "stale"}


def build_refresh_state(last_refreshed: Any = None, *, ttl_seconds: int = 300, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    last = _parse_time(last_refreshed)
    status = classify_refresh_state(last, ttl_seconds=ttl_seconds, now=now)
    age_seconds = None if last is None else max(0.0, (now - last).total_seconds())
    return {
        "last_refreshed": last.isoformat() if last else None,
        "now": now.isoformat(),
        "ttl_seconds": ttl_seconds,
        "age_seconds": age_seconds,
        "status": status,
        "should_refresh": should_refresh(last, ttl_seconds=ttl_seconds, now=now),
    }


def build_refresh_control_payload(last_refreshed: Any = None, *, ttl_seconds: int = 300, label: str = "Refresh") -> dict[str, Any]:
    state = build_refresh_state(last_refreshed, ttl_seconds=ttl_seconds)
    return {
        **state,
        "label": label,
        "tooltip": f"{label}. Current source state is {state['status']}.",
        "disabled": False,
    }
