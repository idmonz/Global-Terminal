from __future__ import annotations

from typing import Any

from .data_status import DataResult


LEDGER_STATUSES = [
    "configured",
    "contacted",
    "successful",
    "live/fresh",
    "cached",
    "stale",
    "rate-limited",
    "forbidden/subscription-blocked",
    "missing-key",
    "unavailable",
    "proxy/static",
]


def _payload(row: Any) -> dict[str, Any]:
    if isinstance(row, DataResult):
        return row.to_dict()
    if isinstance(row, dict):
        return dict(row)
    return {"provider": str(row), "source": "", "status": "unavailable", "ok": False}


def _evidence_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in ["status", "source", "provider", "coverage", "warning", "error", "caveat", "freshness"]
    ).lower()


def _row_count(data: Any) -> int | None:
    if data is None:
        return None
    if hasattr(data, "shape"):
        try:
            return int(data.shape[0])
        except Exception:
            return None
    if isinstance(data, (list, tuple, set)):
        return len(data)
    if isinstance(data, dict):
        for key in ["data", "items", "rows", "features", "articles", "news", "natural", "crypto"]:
            value = data.get(key)
            if isinstance(value, (list, tuple, set)):
                return len(value)
        return 1 if data else 0
    return None


def classify_provider_ledger_status(row: Any) -> str:
    payload = _payload(row)
    text = _evidence_text(payload)
    status = str(payload.get("status") or payload.get("freshness") or "").lower()
    ok = payload.get("ok")
    if "missing optional environment variable" in text or "missing api key" in text or "missing-key" in text or (payload.get("paid_required") and ok is False):
        return "missing-key"
    if "429" in text or "rate limited" in text or "rate-limited" in text:
        return "rate-limited"
    if "403" in text or "401" in text or "forbidden" in text or "unauthorized" in text or "subscription" in text:
        return "forbidden/subscription-blocked"
    if "proxy" in text or "static" in text or payload.get("estimated"):
        return "proxy/static"
    if status == "stale" or "stale cached" in text:
        return "stale"
    if ok is False or status in {"missing", "error", "unavailable"}:
        return "unavailable"
    if payload.get("cached"):
        return "cached"
    if status == "configured" and not payload.get("contacted"):
        return "configured"
    if status == "contacted" and not payload.get("successful"):
        return "contacted"
    if status == "successful":
        return "successful"
    if status in {"fresh", "available", "ok", "free_mode", "no_key_fallback"} or ok is True:
        return "live/fresh"
    return "unavailable"


def recommended_action_for_status(status: str) -> str:
    return {
        "live/fresh": "No action; keep monitoring freshness and row counts.",
        "cached": "Keep visible with cached badge; refresh when the provider is reachable.",
        "stale": "Show stale badge and retry before relying on the payload.",
        "rate-limited": "Wait for provider rate limit reset or use stale/cache fallback.",
        "forbidden/subscription-blocked": "Review provider terms, key, subscription, or public access policy.",
        "missing-key": "Configure the optional provider key or keep the layer unavailable.",
        "unavailable": "Keep the surface disabled or show an explicit unavailable state.",
        "proxy/static": "Treat as context only; do not label it as live telemetry.",
    }.get(status, "Inspect provider evidence before displaying this payload.")


def build_provider_health_ledger(results: list[Any] | None = None) -> list[dict[str, Any]]:
    rows = []
    for result in results or []:
        payload = _payload(result)
        status = classify_provider_ledger_status(payload)
        source = payload.get("source") or payload.get("source_url") or ""
        data = result.data if isinstance(result, DataResult) else payload.get("data")
        rows.append(
            {
                "provider": payload.get("provider", ""),
                "source": source,
                "status": status,
                "ok": bool(payload.get("ok")),
                "availability": "available" if status in {"live/fresh", "cached", "successful"} else "limited" if status in {"stale", "rate-limited", "proxy/static", "contacted"} else "unavailable",
                "row_count": _row_count(data),
                "fetched_at": payload.get("fetched_at"),
                "age_seconds": payload.get("age_seconds"),
                "stale_after_seconds": payload.get("stale_after_seconds"),
                "cached": bool(payload.get("cached")),
                "estimated": bool(payload.get("estimated")),
                "paid_required": bool(payload.get("paid_required")),
                "coverage": payload.get("coverage", "unknown"),
                "warning": payload.get("warning"),
                "error": payload.get("error"),
                "recommended_action": recommended_action_for_status(status),
                "caveat": payload.get("caveat") or "",
            }
        )
    return rows


def summarize_provider_health_ledger(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    ledger = rows or []
    counts: dict[str, int] = {status: 0 for status in LEDGER_STATUSES}
    for row in ledger:
        status = str(row.get("status") or "unavailable")
        counts[status] = counts.get(status, 0) + 1
    available = (
        counts.get("live/fresh", 0)
        + counts.get("cached", 0)
        + counts.get("successful", 0)
    )
    limited = (
        counts.get("stale", 0)
        + counts.get("rate-limited", 0)
        + counts.get("proxy/static", 0)
        + counts.get("contacted", 0)
    )
    blocked = counts.get("forbidden/subscription-blocked", 0) + counts.get("missing-key", 0) + counts.get("unavailable", 0)
    if not ledger:
        ledger_status = "empty"
    elif blocked == 0 and limited == 0:
        ledger_status = "full_success"
    elif available or limited or counts.get("configured", 0):
        ledger_status = "partial_success"
    else:
        ledger_status = "unavailable"
    return {
        "provider_count": len(ledger),
        "available_count": available,
        "limited_count": limited,
        "blocked_count": blocked,
        "configured_only_count": counts.get("configured", 0),
        "status_counts": counts,
        "ledger_status": ledger_status,
        "caveat": "Partial success keeps successful providers visible while blocked/rate-limited feeds remain explicit.",
    }


def build_provider_health_snapshot(results: list[Any] | None = None) -> dict[str, Any]:
    ledger = build_provider_health_ledger(results)
    return {"ledger": ledger, "summary": summarize_provider_health_ledger(ledger)}


def compute_provider_health_score(results: list[dict[str, Any]] | None = None) -> float:
    rows = results or []
    if not rows:
        return 0.0
    weights = {
        "live/fresh": 1.0,
        "cached": 0.85,
        "stale": 0.55,
        "rate-limited": 0.45,
        "forbidden/subscription-blocked": 0.25,
        "missing-key": 0.2,
        "unavailable": 0.0,
        "proxy/static": 0.5,
        "available": 1.0,
        "dry_run": 0.8,
        "configured": 0.9,
        "no_key_fallback": 0.65,
        "historical_only": 0.55,
        "missing_key": 0.2,
        "error": 0.0,
    }
    score = sum(weights.get(str(_payload(row).get("status")), 0.5) for row in rows) / len(rows) * 100
    return round(score, 1)


def build_provider_health_summary(results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = results or []
    score = compute_provider_health_score(rows)
    ledger_summary = summarize_provider_health_ledger(rows if rows and "availability" in _payload(rows[0]) else [])
    return {
        "provider_count": len(rows),
        "ready_count": sum(1 for row in rows if _payload(row).get("ok")),
        "gap_count": sum(1 for row in rows if _payload(row).get("status") in {"missing_key", "missing-key", "error", "unavailable", "forbidden/subscription-blocked"}),
        "historical_only_count": sum(1 for row in rows if _payload(row).get("status") == "historical_only"),
        "score": score,
        "label": "ready" if score >= 80 else "limited" if score >= 50 else "gap",
        "ledger_status": ledger_summary["ledger_status"],
    }


def build_provider_health_cards(results: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    summary = build_provider_health_summary(results)
    return [
        {"title": "Provider Health", "summary": f"Score {summary['score']} across {summary['provider_count']} providers.", "severity": "low" if summary["label"] == "ready" else "watch", "tags": ["provider health"]},
        {"title": "Provider Gaps", "summary": f"{summary['gap_count']} missing or unavailable providers.", "severity": "medium" if summary["gap_count"] else "low", "tags": ["data gap"]},
    ]
