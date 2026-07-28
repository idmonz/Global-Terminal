from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from .data_status import DataResult

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


def _source_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, DataResult):
        return item.to_dict()
    if isinstance(item, dict):
        return dict(item)
    return {"source": str(item), "status": "unknown", "ok": False}


def compute_freshness_status(value: Any = None, *, stale_after_seconds: int = 3600, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if isinstance(value, DataResult):
        payload = value.to_dict()
        payload["label"] = payload.get("status", "unknown")
        payload["severity"] = _severity_for_status(payload["label"])
        return payload
    payload = _source_dict(value) if isinstance(value, dict) else {}
    fetched_at = _to_datetime(payload.get("fetched_at") if payload else value)
    if fetched_at is None:
        status = str(payload.get("status", "missing") if payload else "missing").lower()
        return {
            **payload,
            "status": status,
            "label": status,
            "age_seconds": None,
            "stale_after_seconds": stale_after_seconds,
            "severity": _severity_for_status(status),
        }
    age = max(0.0, (now - fetched_at).total_seconds())
    status = "fresh" if age <= stale_after_seconds else "stale"
    if payload.get("estimated"):
        status = "estimated"
    if payload.get("error"):
        status = "error"
    if payload.get("ok") is False and not payload.get("estimated"):
        status = "missing" if status != "error" else status
    return {
        **payload,
        "status": status,
        "label": status,
        "age_seconds": round(age, 1),
        "stale_after_seconds": stale_after_seconds,
        "severity": _severity_for_status(status),
    }


def _severity_for_status(status: str | None) -> str:
    normalized = (status or "unknown").lower()
    if normalized == "fresh":
        return "low"
    if normalized == "estimated":
        return "watch"
    if normalized == "stale":
        return "medium"
    if normalized in {"missing", "error"}:
        return "high"
    return "info"


def source_badge_payload(source: str, provider: str = "", status: Any = None) -> dict[str, Any]:
    freshness = compute_freshness_status(status)
    return {
        "source": source,
        "provider": provider or freshness.get("provider", ""),
        "status": freshness.get("status", "unknown"),
        "severity": freshness.get("severity", "info"),
        "age_seconds": freshness.get("age_seconds"),
        "coverage": freshness.get("coverage", "unknown"),
        "estimated": bool(freshness.get("estimated")),
        "paid_required": bool(freshness.get("paid_required")),
        "warning": freshness.get("warning"),
        "error": freshness.get("error"),
    }


def source_freshness_table(statuses: Iterable[Any] | None = None):
    rows = []
    for item in statuses or []:
        payload = compute_freshness_status(item)
        rows.append(
            {
                "provider": payload.get("provider", ""),
                "source": payload.get("source", ""),
                "status": payload.get("status", "unknown"),
                "age_minutes": None if payload.get("age_seconds") is None else round(float(payload["age_seconds"]) / 60.0, 1),
                "coverage": payload.get("coverage", "unknown"),
                "estimated": bool(payload.get("estimated")),
                "cached": bool(payload.get("cached")),
                "paid_required": bool(payload.get("paid_required")),
                "warning": payload.get("warning"),
                "error": payload.get("error"),
            }
        )
    if pd is None:
        return rows
    return pd.DataFrame(rows)


def stale_source_warning(statuses: Iterable[Any] | None = None) -> str | None:
    table = source_freshness_table(statuses)
    if table is None or getattr(table, "empty", True):
        return None
    stale = table[table["status"].astype(str).str.lower().eq("stale")]
    if stale.empty:
        return None
    sources = ", ".join(stale["source"].astype(str).head(4).tolist())
    return f"Source stale: {sources}"


def missing_source_warning(statuses: Iterable[Any] | None = None) -> str | None:
    table = source_freshness_table(statuses)
    if table is None or getattr(table, "empty", True):
        return "Source missing: no status records available."
    missing = table[table["status"].astype(str).str.lower().isin(["missing", "error"])]
    if missing.empty:
        return None
    sources = ", ".join(missing["source"].astype(str).head(4).tolist())
    return f"Source missing: {sources}"
