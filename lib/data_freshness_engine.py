from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = pd.to_datetime(value, utc=True, errors="coerce") if pd is not None else None
        if parsed is None or pd.isna(parsed):
            return None
        return parsed.to_pydatetime()
    except Exception:
        return None


def compute_data_freshness(fetched_at: Any = None, *, stale_after_seconds: int = 900, now: Any = None, ok: bool = True, is_estimated: bool = False) -> dict[str, Any]:
    if not ok:
        return {"status": "error", "age_seconds": None, "stale_after_seconds": stale_after_seconds, "fetched_at": fetched_at}
    if is_estimated:
        return {"status": "estimated", "age_seconds": None, "stale_after_seconds": stale_after_seconds, "fetched_at": fetched_at}
    fetched = _to_datetime(fetched_at) or datetime.now(timezone.utc)
    current = _to_datetime(now) or datetime.now(timezone.utc)
    age = max(0.0, (current - fetched).total_seconds())
    return {"status": classify_freshness(age, stale_after_seconds=stale_after_seconds), "age_seconds": round(age, 1), "stale_after_seconds": stale_after_seconds, "fetched_at": fetched.isoformat()}


def classify_freshness(age_seconds: float | None = None, *, stale_after_seconds: int = 900, status: str | None = None) -> str:
    if status in {"error", "missing", "estimated", "fresh", "stale"}:
        return status
    if age_seconds is None:
        return "missing"
    return "stale" if float(age_seconds) > stale_after_seconds else "fresh"


def build_freshness_badges(results: list[Any] | None = None) -> list[dict[str, Any]]:
    badges: list[dict[str, Any]] = []
    for result in results or []:
        status = result.refreshed_status() if hasattr(result, "refreshed_status") else getattr(result, "freshness", "unknown")
        badges.append(
            {
                "provider": getattr(result, "provider", ""),
                "source": getattr(result, "source", ""),
                "status": status,
                "age_seconds": getattr(result, "age_seconds", None),
                "label": str(status).replace("_", " ").title(),
            }
        )
    return badges


def build_freshness_table(results: list[Any] | None = None):
    rows = []
    for badge in build_freshness_badges(results):
        rows.append({**badge, "warning": stale_data_warning(badge["status"]) if badge["status"] == "stale" else None})
    return pd.DataFrame(rows) if pd is not None else rows


def stale_data_warning(status_or_result: Any) -> str | None:
    status = status_or_result.refreshed_status() if hasattr(status_or_result, "refreshed_status") else str(status_or_result)
    if status == "stale":
        return "Data may be stale; verify source freshness before using this panel."
    if status == "estimated":
        return "Data is estimated or proxy-labeled."
    if status in {"missing", "error"}:
        return "Data is unavailable from the configured provider route."
    return None
