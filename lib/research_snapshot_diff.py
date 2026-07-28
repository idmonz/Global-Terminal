from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .alert_state_machine import apply_alert_cooldown, apply_alert_expiry
from .alert_store import (
    create_alert_rule,
    get_alert_rule,
    list_alert_events,
    list_alert_rules,
    store_alert_event,
    update_alert_rule,
)
from .research_snapshot import MAX_RESEARCH_PROVIDER_CALLS
from .research_workspace_db import execute_query, json_dumps, json_loads


RESEARCH_SNAPSHOT_DIFF_VERSION = "research_snapshot_diff.v1"
WATCHLIST_REFRESH_OPERATIONS_VERSION = "watchlist_refresh_operations.v1"
WATCHLIST_CHANGE_ALERT_VERSION = "watchlist_change_alert.v1"
_SAFE_LIST_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
_SEVERITY_RANK = {"info": 0, "material": 1, "high": 2, "critical": 3}
_SOURCE_RANK = {
    "live/fresh": 6,
    "fresh": 6,
    "cached": 5,
    "fixture": 4,
    "stale": 3,
    "rate-limited": 2,
    "missing-key": 1,
    "unavailable": 0,
    "provider-error": 0,
    "error": 0,
}
_PERFORMANCE_FIELDS = ("return_1w_pct", "return_1m_pct", "return_3m_pct")
_FUNDAMENTAL_FIELDS = (
    "market_cap",
    "revenue_ttm",
    "eps",
    "pe_ratio",
    "annual_dividend_per_share",
    "dividend_yield",
)


def build_research_snapshot_diff(
    previous_job: dict[str, Any] | None,
    current_job: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = _iso(now)
    previous = dict(previous_job or {})
    current = dict(current_job or {})
    if not current:
        return _empty_diff("no-snapshot", previous, current, generated_at)
    if not previous:
        return _empty_diff("only-one-snapshot", previous, current, generated_at)
    previous_list = str(previous.get("list_id") or "")
    current_list = str(current.get("list_id") or "")
    if not previous_list or previous_list != current_list:
        raise ValueError("Research Snapshot diff requires two snapshots from the same watchlist.")
    if str(previous.get("status")) != "completed" or str(current.get("status")) != "completed":
        return _empty_diff("incompatible-snapshot", previous, current, generated_at)

    previous_rows = _rows_by_symbol(previous)
    current_rows = _rows_by_symbol(current)
    changes: list[dict[str, Any]] = []

    for symbol in sorted(previous_rows.keys() - current_rows.keys()):
        changes.append(
            _change(
                symbol=symbol,
                change_type="symbol",
                field="membership",
                transition="removed",
                before=symbol,
                after=None,
                unit="identity",
                severity="material",
                previous_row=previous_rows[symbol],
                current_row=None,
                observation=f"{symbol} is absent from the current saved snapshot.",
            )
        )
    for symbol in sorted(current_rows.keys() - previous_rows.keys()):
        changes.append(
            _change(
                symbol=symbol,
                change_type="symbol",
                field="membership",
                transition="added",
                before=None,
                after=symbol,
                unit="identity",
                severity="material",
                previous_row=None,
                current_row=current_rows[symbol],
                observation=f"{symbol} appears in the current saved snapshot.",
            )
        )

    for symbol in sorted(previous_rows.keys() & current_rows.keys()):
        before_row = previous_rows[symbol]
        after_row = current_rows[symbol]
        changes.extend(_price_changes(symbol, before_row, after_row))
        changes.extend(_performance_changes(symbol, before_row, after_row))
        changes.extend(_fundamental_changes(symbol, before_row, after_row))
        changes.extend(_event_changes(symbol, before_row, after_row))
        changes.extend(_news_changes(symbol, before_row, after_row))
        source_change = _source_status_change(symbol, before_row, after_row)
        if source_change:
            changes.append(source_change)

    ordered = sorted(
        changes,
        key=lambda row: (
            -_SEVERITY_RANK.get(str(row.get("severity")), 0),
            str(row.get("symbol")),
            str(row.get("change_type")),
            str(row.get("field")),
            str(row.get("change_id")),
        ),
    )
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for row in ordered:
        by_type[str(row["change_type"])] = by_type.get(str(row["change_type"]), 0) + 1
        by_severity[str(row["severity"])] = by_severity.get(str(row["severity"]), 0) + 1
    return {
        "diff_version": RESEARCH_SNAPSHOT_DIFF_VERSION,
        "comparison_status": "ready",
        "list_id": current_list,
        "previous_snapshot_id": previous.get("job_id"),
        "current_snapshot_id": current.get("job_id"),
        "previous_snapshot_at": previous.get("completed_at") or previous.get("started_at"),
        "current_snapshot_at": current.get("completed_at") or current.get("started_at"),
        "generated_at": generated_at,
        "provider_call_count": 0,
        "changes": ordered,
        "summary": {
            "change_count": len(ordered),
            "symbol_count": len({str(row["symbol"]) for row in ordered}),
            "by_type": by_type,
            "by_severity": by_severity,
            "has_material_change": any(_SEVERITY_RANK.get(str(row.get("severity")), 0) >= 1 for row in ordered),
        },
        "thresholds": {
            "price_relative_pct": 1.0,
            "performance_percentage_points": 1.0,
            "fundamental_relative_pct": 5.0,
        },
        "source_status": _combined_source_status(current_rows.values()),
        "caveat": "Changes compare two saved observations. They do not establish causality, investment significance, or a recommended action.",
        "data_gap": None if ordered else "No material normalized change crossed the documented thresholds.",
        "not_financial_advice": True,
    }


def build_refresh_operations_contract(
    jobs: list[dict[str, Any]] | None,
    *,
    now: datetime | None = None,
    background_enabled: bool = False,
    busy: bool = False,
) -> dict[str, Any]:
    ordered = sorted(
        [dict(row) for row in jobs or [] if isinstance(row, dict)],
        key=lambda row: (str(row.get("started_at") or ""), str(row.get("job_id") or "")),
        reverse=True,
    )
    successes = [row for row in ordered if row.get("status") == "completed" and _records(row.get("rows"))]
    last_attempt = ordered[0] if ordered else {}
    last_success = successes[0] if successes else {}
    previous_success = successes[1] if len(successes) > 1 else {}
    budget = _record(last_success.get("provider_budget"))
    maximum_calls = min(
        int(last_success.get("provider_call_budget") or budget.get("maximum_calls") or MAX_RESEARCH_PROVIDER_CALLS),
        MAX_RESEARCH_PROVIDER_CALLS,
    )
    actual_calls = min(
        int(last_success.get("provider_call_count") or budget.get("actual_calls") or 0),
        maximum_calls,
    )
    last_status = str(last_attempt.get("status") or "not-run")
    readiness = "busy" if busy else "degraded" if last_status in {"failed", "partial"} else "ready" if last_success else "not-run"
    return {
        "operations_version": WATCHLIST_REFRESH_OPERATIONS_VERSION,
        "generated_at": _iso(now),
        "mode": "manual-bounded",
        "readiness": readiness,
        "installed_background_service": False,
        "running": bool(busy),
        "last_attempt": _public_job(last_attempt),
        "last_success": _public_job(last_success),
        "previous_success": _public_job(previous_success),
        "next_eligible_at": budget.get("next_safe_refresh_at"),
        "queue_depth": int(last_attempt.get("queue_depth") or 0),
        "overlap_status": "busy" if busy else "idle",
        "budget": {
            "maximum_calls": maximum_calls,
            "actual_calls": actual_calls,
            "cache_hits": int(budget.get("cache_hits") or 0),
            "stale_hits": int(budget.get("stale_hits") or 0),
            "failed_calls": int(budget.get("failed_calls") or 0),
            "blocked_calls": int(budget.get("blocked_calls") or 0),
            "skipped_calls": int(budget.get("skipped_calls") or 0),
            "actual_calls_by_operation": _record(budget.get("actual_calls_by_operation")),
        },
        "background": {
            "configured": bool(background_enabled),
            "enabled": bool(background_enabled),
            "kill_switch_engaged": not bool(background_enabled),
            "installed": False,
            "running": False,
            "status": "ready-not-installed" if background_enabled else "disabled-by-default",
        },
        "manual_refresh": {
            "available": not busy,
            "action": "POST /api/watchlist-desk/lists/{list_id}/materialize",
            "maximum_symbols": 5,
            "maximum_provider_calls": MAX_RESEARCH_PROVIDER_CALLS,
        },
        "bounded_event_history": [_public_job(row) for row in ordered[:10]],
        "source_status": "stale" if last_status == "failed" and last_success else last_status,
        "caveat": "The background scheduler is not installed. Manual refresh is bounded and the latest failed attempt never replaces the last successful snapshot.",
        "data_gap": "No completed Research Snapshot is available." if not last_success else None,
        "not_financial_advice": True,
    }


def upsert_watchlist_change_rule(
    list_id: str,
    *,
    enabled: bool,
    minimum_severity: str = "material",
    cooldown_minutes: int = 60,
    expires_at: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_list = _normalize_list_id(list_id)
    severity = str(minimum_severity or "material").lower()
    if severity not in _SEVERITY_RANK:
        raise ValueError("Unsupported minimum change severity.")
    cooldown = max(0, min(int(cooldown_minutes), 10_080))
    metadata = {
        "kind": WATCHLIST_CHANGE_ALERT_VERSION,
        "list_id": normalized_list,
        "minimum_severity": severity,
        "delivery": "preview-only",
        "opt_in": bool(enabled),
        "hosted_delivery": "unavailable",
    }
    existing = next(
        (
            row
            for row in list_alert_rules(active_only=False, db_path=db_path)
            if _record(row.get("metadata_json")).get("kind") == WATCHLIST_CHANGE_ALERT_VERSION
            and _record(row.get("metadata_json")).get("list_id") == normalized_list
        ),
        None,
    )
    if existing:
        updated = update_alert_rule(
            str(existing["alert_id"]),
            db_path=db_path,
            active=enabled,
            cooldown_minutes=cooldown,
            expires_at=expires_at,
            metadata_json=metadata,
        )
        return updated or existing
    return create_alert_rule(
        watch_item_id=f"watchlist:{normalized_list}",
        scope="watchlist_change",
        metric="snapshot_change",
        operator="status_is",
        threshold=severity,
        window="between-successful-snapshots",
        severity=severity,
        cooldown_minutes=cooldown,
        active=enabled,
        expires_at=expires_at,
        metadata=metadata,
        db_path=db_path,
    )


def build_change_alert_preview(
    diff: dict[str, Any],
    *,
    rule: dict[str, Any] | None,
    events: list[dict[str, Any]] | None,
    now: datetime | None = None,
    kill_switch: bool = False,
) -> dict[str, Any]:
    current_time = _as_utc(now)
    event_rows = [dict(row) for row in events or [] if isinstance(row, dict)]
    base = {
        "alert_version": WATCHLIST_CHANGE_ALERT_VERSION,
        "delivery": "preview-only",
        "hosted_delivery": "unavailable",
        "generated_at": current_time.replace(microsecond=0).isoformat(),
        "opt_in": bool(rule and rule.get("active")),
        "kill_switch_engaged": bool(kill_switch),
        "candidates": [],
        "candidate_count": 0,
        "eligible_count": 0,
        "duplicate_count": 0,
        "acknowledged_count": 0,
        "not_financial_advice": True,
    }
    if not rule or not rule.get("active"):
        return {**base, "status": "disabled", "data_gap": "Enable a local-private preview rule to evaluate saved changes."}
    if kill_switch:
        return {**base, "status": "killed", "data_gap": "The alert preview kill switch is engaged."}

    expiry = apply_alert_expiry(rule, now=current_time)
    if expiry.get("expired"):
        return {**base, "status": "expired", "data_gap": expiry.get("message")}
    minimum = str(_record(rule.get("metadata_json")).get("minimum_severity") or rule.get("threshold") or "material")
    minimum_rank = _SEVERITY_RANK.get(minimum, 1)
    changes = [
        row
        for row in _records(diff.get("changes"))
        if _SEVERITY_RANK.get(str(row.get("severity")), 0) >= minimum_rank
    ]
    existing_by_fingerprint = {
        str(_record(row.get("metadata_json")).get("fingerprint")): row
        for row in event_rows
        if _record(row.get("metadata_json")).get("fingerprint")
    }
    cooldown = apply_alert_cooldown(rule, now=current_time)
    candidates = []
    for change in changes:
        fingerprint = _hash(
            {
                "alert_id": rule.get("alert_id"),
                "list_id": diff.get("list_id"),
                "change_id": change.get("change_id"),
            }
        )
        existing = existing_by_fingerprint.get(fingerprint)
        acknowledged = bool(_record((existing or {}).get("metadata_json")).get("acknowledged_at"))
        status = "acknowledged" if acknowledged else "duplicate" if existing else "cooldown" if cooldown.get("in_cooldown") else "preview-ready"
        candidates.append(
            {
                "fingerprint": fingerprint,
                "change_id": change.get("change_id"),
                "symbol": change.get("symbol"),
                "change_type": change.get("change_type"),
                "severity": change.get("severity"),
                "status": status,
                "event_id": (existing or {}).get("event_id"),
                "acknowledgement_status": "acknowledged" if acknowledged else "unacknowledged",
                "observation": change.get("observation"),
                "evidence": change.get("evidence"),
            }
        )
    duplicate_count = sum(1 for row in candidates if row["status"] in {"duplicate", "acknowledged"})
    acknowledged_count = sum(1 for row in candidates if row["status"] == "acknowledged")
    eligible_count = sum(1 for row in candidates if row["status"] == "preview-ready")
    status = (
        "ready"
        if eligible_count
        else "deduped"
        if duplicate_count
        else "cooldown"
        if cooldown.get("in_cooldown") and candidates
        else "no-candidates"
    )
    return {
        **base,
        "status": status,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "eligible_count": eligible_count,
        "duplicate_count": duplicate_count,
        "acknowledged_count": acknowledged_count,
        "cooldown_minutes": int(rule.get("cooldown_minutes") or 0),
        "expires_at": rule.get("expires_at"),
        "data_gap": None if candidates else "No saved change meets the local minimum severity.",
    }


def persist_change_alert_previews(
    list_id: str,
    diff: dict[str, Any],
    *,
    db_path: str | Path | None = None,
    now: datetime | None = None,
    kill_switch: bool = False,
) -> dict[str, Any]:
    normalized_list = _normalize_list_id(list_id)
    rule = _change_rule(normalized_list, db_path=db_path)
    events = _change_events(normalized_list, db_path=db_path)
    preview = build_change_alert_preview(
        diff,
        rule=rule,
        events=events,
        now=now,
        kill_switch=kill_switch,
    )
    stored = []
    for candidate in preview.get("candidates", []):
        if candidate.get("status") != "preview-ready" or not rule:
            continue
        event = store_alert_event(
            {
                "alert_id": rule.get("alert_id"),
                "watch_item_id": f"watchlist:{normalized_list}",
                "status": "preview",
                "triggered": True,
                "severity": candidate.get("severity") or "material",
                "metric": "snapshot_change",
                "observed_value": candidate.get("change_id"),
                "threshold": rule.get("threshold"),
                "message": candidate.get("observation") or "Saved snapshot change.",
                "source_snapshot_json": candidate.get("evidence") or {},
                "data_confidence": "source-preserving-observation",
                "created_at": _iso(now),
                "metadata_json": {
                    "kind": WATCHLIST_CHANGE_ALERT_VERSION,
                    "list_id": normalized_list,
                    "fingerprint": candidate.get("fingerprint"),
                    "change_id": candidate.get("change_id"),
                    "acknowledged_at": None,
                    "delivery": "preview-only",
                },
            },
            db_path=db_path,
        )
        stored.append(event)
    if stored and rule:
        update_alert_rule(
            str(rule["alert_id"]),
            db_path=db_path,
            triggered=True,
            last_triggered_at=_iso(now),
        )
    return {
        **preview,
        "stored_count": len(stored),
        "events": stored,
    }


def acknowledge_change_alert_event(
    event_id: str,
    *,
    db_path: str | Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    normalized = str(event_id or "").strip()
    if not re.fullmatch(r"event_[a-f0-9]{12}", normalized):
        raise ValueError("Invalid local alert event ID.")
    row = execute_query(
        "SELECT * FROM alert_events WHERE event_id = ?",
        (normalized,),
        fetch=True,
        one=True,
        db_path=db_path,
    )
    if not isinstance(row, dict):
        raise KeyError("Alert preview event not found.")
    metadata = json_loads(row.get("metadata_json"), {})
    if not isinstance(metadata, dict) or metadata.get("kind") != WATCHLIST_CHANGE_ALERT_VERSION:
        raise ValueError("Alert event is not a Watchlist change preview.")
    acknowledged_at = _iso(now)
    metadata["acknowledged_at"] = acknowledged_at
    execute_query(
        "UPDATE alert_events SET status = ?, metadata_json = ? WHERE event_id = ?",
        ("acknowledged", json_dumps(metadata), normalized),
        db_path=db_path,
    )
    return {
        "event_id": normalized,
        "status": "acknowledged",
        "acknowledgement_status": "acknowledged",
        "acknowledged_at": acknowledged_at,
        "delivery": "preview-only",
    }


def change_alert_readiness_for_list(
    list_id: str,
    diff: dict[str, Any],
    *,
    db_path: str | Path | None = None,
    now: datetime | None = None,
    kill_switch: bool = False,
) -> dict[str, Any]:
    normalized_list = _normalize_list_id(list_id)
    return build_change_alert_preview(
        diff,
        rule=_change_rule(normalized_list, db_path=db_path),
        events=_change_events(normalized_list, db_path=db_path),
        now=now,
        kill_switch=kill_switch,
    )


def _empty_diff(
    status: str,
    previous: dict[str, Any],
    current: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "diff_version": RESEARCH_SNAPSHOT_DIFF_VERSION,
        "comparison_status": status,
        "list_id": current.get("list_id") or previous.get("list_id"),
        "previous_snapshot_id": previous.get("job_id"),
        "current_snapshot_id": current.get("job_id"),
        "previous_snapshot_at": previous.get("completed_at") or previous.get("started_at"),
        "current_snapshot_at": current.get("completed_at") or current.get("started_at"),
        "generated_at": generated_at,
        "provider_call_count": 0,
        "changes": [],
        "summary": {"change_count": 0, "symbol_count": 0, "by_type": {}, "by_severity": {}, "has_material_change": False},
        "thresholds": {
            "price_relative_pct": 1.0,
            "performance_percentage_points": 1.0,
            "fundamental_relative_pct": 5.0,
        },
        "source_status": "unavailable",
        "caveat": "Two completed same-list snapshots are required for a change comparison.",
        "data_gap": status,
        "not_financial_advice": True,
    }


def _price_changes(symbol: str, before_row: dict[str, Any], after_row: dict[str, Any]) -> list[dict[str, Any]]:
    before = _number(_record(before_row.get("quote")).get("last_price"))
    after = _number(_record(after_row.get("quote")).get("last_price"))
    if before is None or after is None or before == 0:
        return []
    relative_pct = (after / before - 1.0) * 100.0
    if abs(relative_pct) < 1.0:
        return []
    severity = "critical" if abs(relative_pct) >= 7 else "high" if abs(relative_pct) >= 3 else "material"
    return [
        _change(
            symbol=symbol,
            change_type="price",
            field="last_price",
            transition="increased" if relative_pct > 0 else "decreased",
            before=before,
            after=after,
            unit="quote-currency",
            severity=severity,
            previous_row=before_row,
            current_row=after_row,
            observation=f"{symbol} saved price changed {relative_pct:+.2f}% between snapshots.",
            magnitude={"relative_pct": round(relative_pct, 6)},
        )
    ]


def _performance_changes(symbol: str, before_row: dict[str, Any], after_row: dict[str, Any]) -> list[dict[str, Any]]:
    before = _record(before_row.get("performance"))
    after = _record(after_row.get("performance"))
    output = []
    for field in _PERFORMANCE_FIELDS:
        left = _number(before.get(field))
        right = _number(after.get(field))
        if left is None or right is None:
            continue
        delta = right - left
        if abs(delta) < 1.0:
            continue
        output.append(
            _change(
                symbol=symbol,
                change_type="performance",
                field=field,
                transition="increased" if delta > 0 else "decreased",
                before=left,
                after=right,
                unit="percentage-points",
                severity="material" if abs(delta) < 5 else "high",
                previous_row=before_row,
                current_row=after_row,
                observation=f"{symbol} {field} changed {delta:+.2f} percentage points.",
                magnitude={"percentage_point_delta": round(delta, 6)},
            )
        )
    return output


def _fundamental_changes(symbol: str, before_row: dict[str, Any], after_row: dict[str, Any]) -> list[dict[str, Any]]:
    before = _record(_record(before_row.get("financials")).get("metrics"))
    after = _record(_record(after_row.get("financials")).get("metrics"))
    output = []
    for field in _FUNDAMENTAL_FIELDS:
        left = _number(before.get(field))
        right = _number(after.get(field))
        if left is None or right is None or left == 0:
            continue
        relative_pct = (right / left - 1.0) * 100.0
        if abs(relative_pct) < 5.0:
            continue
        output.append(
            _change(
                symbol=symbol,
                change_type="fundamental",
                field=field,
                transition="increased" if relative_pct > 0 else "decreased",
                before=left,
                after=right,
                unit="provider-reported",
                severity="high" if abs(relative_pct) >= 20 else "material",
                previous_row=before_row,
                current_row=after_row,
                observation=f"{symbol} provider-reported {field} changed {relative_pct:+.2f}% between snapshots.",
                magnitude={"relative_pct": round(relative_pct, 6)},
            )
        )
    return output


def _event_changes(symbol: str, before_row: dict[str, Any], after_row: dict[str, Any]) -> list[dict[str, Any]]:
    before_events = _events_by_type(before_row)
    after_events = _events_by_type(after_row)
    output = []
    for event_type in sorted(before_events.keys() | after_events.keys()):
        left = before_events.get(event_type)
        right = after_events.get(event_type)
        left_date = _event_date(left)
        right_date = _event_date(right)
        if left_date == right_date:
            continue
        transition = "scheduled" if not left_date else "removed" if not right_date else "rescheduled"
        output.append(
            _change(
                symbol=symbol,
                change_type="event",
                field=event_type,
                transition=transition,
                before=left_date,
                after=right_date,
                unit="date",
                severity="material",
                previous_row=left or before_row,
                current_row=right or after_row,
                observation=f"{symbol} {event_type} changed from {left_date or 'unavailable'} to {right_date or 'unavailable'}.",
            )
        )
    return output


def _news_changes(symbol: str, before_row: dict[str, Any], after_row: dict[str, Any]) -> list[dict[str, Any]]:
    before_news = {_news_id(row): row for row in _exact_news(before_row)}
    after_news = {_news_id(row): row for row in _exact_news(after_row)}
    output = []
    for news_id in sorted(after_news.keys() - before_news.keys()):
        row = after_news[news_id]
        output.append(
            _change(
                symbol=symbol,
                change_type="news",
                field="exact_news",
                transition="added",
                before=None,
                after=row.get("title"),
                unit="headline",
                severity="info",
                previous_row=None,
                current_row=row,
                observation=f"{symbol} has a new exact-symbol headline: {str(row.get('title') or 'Untitled')[:180]}",
            )
        )
    return output


def _source_status_change(symbol: str, before_row: dict[str, Any], after_row: dict[str, Any]) -> dict[str, Any] | None:
    before = _normalize_status(before_row.get("source_status"))
    after = _normalize_status(after_row.get("source_status"))
    if before == after:
        return None
    before_rank = _SOURCE_RANK.get(before, 0)
    after_rank = _SOURCE_RANK.get(after, 0)
    transition = "degraded" if after_rank < before_rank else "recovered" if after_rank > before_rank else "changed"
    severity = "high" if transition == "degraded" and after_rank <= 2 else "material"
    return _change(
        symbol=symbol,
        change_type="source-status",
        field="source_status",
        transition=transition,
        before=before,
        after=after,
        unit="status",
        severity=severity,
        previous_row=before_row,
        current_row=after_row,
        observation=f"{symbol} source status {transition} from {before} to {after}.",
    )


def _change(
    *,
    symbol: str,
    change_type: str,
    field: str,
    transition: str,
    before: Any,
    after: Any,
    unit: str,
    severity: str,
    previous_row: dict[str, Any] | None,
    current_row: dict[str, Any] | None,
    observation: str,
    magnitude: dict[str, Any] | None = None,
) -> dict[str, Any]:
    semantic = {
        "symbol": symbol,
        "change_type": change_type,
        "field": field,
        "transition": transition,
        "before": before,
        "after": after,
        "unit": unit,
    }
    return {
        "change_id": f"change_{_hash(semantic)[:16]}",
        **semantic,
        "severity": severity,
        "magnitude": magnitude or {},
        "observation": observation,
        "interpretation": "observation-only",
        "evidence": {
            "before": _evidence(previous_row),
            "after": _evidence(current_row),
        },
        "not_financial_advice": True,
    }


def _evidence(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    quote = _record(row.get("quote"))
    financials = _record(row.get("financials"))
    return {
        "provider": row.get("provider") or quote.get("provider") or financials.get("provider"),
        "source_url": row.get("source_url") or quote.get("source_url") or financials.get("source_url"),
        "source_status": row.get("source_status") or quote.get("source_status") or financials.get("source_status"),
        "fetched_at": row.get("fetched_at") or quote.get("retrieved_at") or financials.get("fetched_at"),
        "confidence": row.get("confidence"),
        "caveat": row.get("caveat"),
        "data_gap": row.get("data_gap"),
    }


def _public_job(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "job_id": row.get("job_id"),
        "list_id": row.get("list_id"),
        "status": row.get("status"),
        "requested_count": int(row.get("requested_count") or 0),
        "completed_count": int(row.get("completed_count") or 0),
        "failed_count": int(row.get("failed_count") or 0),
        "skipped_count": int(row.get("skipped_count") or 0),
        "provider_call_budget": min(int(row.get("provider_call_budget") or 0), MAX_RESEARCH_PROVIDER_CALLS),
        "provider_call_count": min(
            int(row.get("provider_call_count") or 0),
            min(int(row.get("provider_call_budget") or MAX_RESEARCH_PROVIDER_CALLS), MAX_RESEARCH_PROVIDER_CALLS),
        ),
        "queue_depth": int(row.get("queue_depth") or 0),
        "duration_ms": int(row.get("duration_ms") or 0),
        "started_at": row.get("started_at"),
        "completed_at": row.get("completed_at"),
        "last_error": row.get("last_error"),
    }


def _change_rule(list_id: str, *, db_path: str | Path | None) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in list_alert_rules(active_only=False, db_path=db_path)
            if _record(row.get("metadata_json")).get("kind") == WATCHLIST_CHANGE_ALERT_VERSION
            and _record(row.get("metadata_json")).get("list_id") == list_id
        ),
        None,
    )


def _change_events(list_id: str, *, db_path: str | Path | None) -> list[dict[str, Any]]:
    return [
        row
        for row in list_alert_events(limit=100, db_path=db_path)
        if _record(row.get("metadata_json")).get("kind") == WATCHLIST_CHANGE_ALERT_VERSION
        and _record(row.get("metadata_json")).get("list_id") == list_id
    ]


def _rows_by_symbol(job: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("symbol") or "").upper(): row
        for row in _records(job.get("rows"))
        if row.get("symbol")
    }


def _events_by_type(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    catalysts = _record(row.get("catalysts"))
    events = [*_records(catalysts.get("earnings")), *_records(catalysts.get("dividends"))]
    return {
        str(event.get("event_type") or "event"): event
        for event in events
        if event.get("event_type")
    }


def _event_date(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    return str(row.get("event_date") or row.get("ex_dividend_date") or row.get("payment_date") or "") or None


def _exact_news(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in _records(_record(row.get("catalysts")).get("news"))
        if item.get("exact_symbol_scope") is True or _record(item.get("match_evidence")).get("exact") is True
    ]


def _news_id(row: dict[str, Any]) -> str:
    url = str(row.get("source_url") or "").strip().lower()
    if url:
        return f"url:{url}"
    return _hash(
        {
            "title": " ".join(str(row.get("title") or "").lower().split()),
            "published_at": row.get("published_at"),
        }
    )


def _combined_source_status(rows: Any) -> str:
    statuses = [_normalize_status(row.get("source_status")) for row in rows if isinstance(row, dict)]
    return min(statuses, key=lambda value: _SOURCE_RANK.get(value, 0)) if statuses else "unavailable"


def _normalize_status(value: Any) -> str:
    return str(value or "unavailable").strip().lower()


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _records(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value or [] if isinstance(row, dict)]


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_list_id(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if not _SAFE_LIST_ID.fullmatch(normalized):
        raise ValueError("watchlist_id must be a lowercase URL-safe identifier.")
    return normalized


def _as_utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    return (current if current.tzinfo else current.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _iso(value: datetime | None) -> str:
    return _as_utc(value).replace(microsecond=0).isoformat()
