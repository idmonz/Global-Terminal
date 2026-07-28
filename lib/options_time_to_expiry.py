from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DAYS_IN_YEAR = 365.25


def _parse_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    for parser in (
        lambda s: datetime.fromisoformat(s),
        lambda s: datetime.strptime(s, "%Y-%m-%d"),
        lambda s: datetime.strptime(s, "%Y/%m/%d"),
    ):
        try:
            dt = parser(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def derive_days_to_expiry(expiry: Any, timestamp: Any = None, *, snapshot_timestamp: Any = None) -> dict[str, Any]:
    exp = _parse_dt(expiry)
    base = _parse_dt(timestamp) or _parse_dt(snapshot_timestamp)
    if exp is None:
        return {"ok": False, "days_to_expiry": None, "status": "invalid_expiry", "caveat": "expiry_not_parseable", "research_only": True}
    if base is None:
        return {"ok": False, "days_to_expiry": None, "status": "missing_timestamp", "caveat": "timestamp_required_for_tte", "research_only": True}
    seconds = (exp - base).total_seconds()
    days = seconds / 86400.0
    if seconds <= 0:
        return {"ok": False, "days_to_expiry": 0.0, "status": "expired", "caveat": "expired_option_not_priced_with_positive_tte", "research_only": True}
    return {"ok": True, "days_to_expiry": days, "status": "derived", "caveat": "derived_from_expiry_and_timestamp", "research_only": True}


def derive_time_to_expiry_years(row_or_tte: Any = None, expiry: Any = None, timestamp: Any = None, *, snapshot_timestamp: Any = None) -> dict[str, Any]:
    if isinstance(row_or_tte, dict):
        row = row_or_tte
        supplied = row.get("time_to_expiry_years") or row.get("tte")
        expiry = row.get("expiry", expiry)
        timestamp = row.get("timestamp", timestamp)
        snapshot_timestamp = row.get("snapshot_timestamp", snapshot_timestamp)
    else:
        supplied = row_or_tte
    if supplied not in (None, ""):
        try:
            tte = float(supplied)
        except Exception:
            return {"ok": False, "time_to_expiry_years": None, "status": "invalid_supplied_tte", "caveat": "supplied_tte_not_numeric", "research_only": True}
        if tte <= 0:
            return {"ok": False, "time_to_expiry_years": None, "status": "expired_or_invalid_tte", "caveat": "non_positive_tte_not_priced", "research_only": True}
        return {"ok": True, "time_to_expiry_years": tte, "days_to_expiry": tte * DAYS_IN_YEAR, "status": "supplied", "caveat": "user_supplied_tte", "research_only": True}
    days_payload = derive_days_to_expiry(expiry, timestamp, snapshot_timestamp=snapshot_timestamp)
    if not days_payload.get("ok"):
        return {"ok": False, "time_to_expiry_years": None, "days_to_expiry": days_payload.get("days_to_expiry"), "status": days_payload.get("status"), "caveat": days_payload.get("caveat"), "research_only": True}
    return {"ok": True, "time_to_expiry_years": float(days_payload["days_to_expiry"]) / DAYS_IN_YEAR, "days_to_expiry": days_payload["days_to_expiry"], "status": "derived", "caveat": "derived_from_expiry_and_timestamp", "research_only": True}
