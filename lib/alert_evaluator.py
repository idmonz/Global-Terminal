from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .alert_store import list_alert_rules, store_alert_event, update_alert_rule, list_alert_events
from .alert_metric_resolver import resolve_alert_metric
from .alert_state_machine import apply_alert_cooldown, apply_alert_expiry, classify_alert_transition, get_previous_observed_value, update_alert_state
from .alert_deduper import dedupe_alert_event, build_alert_event_hash


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _compare(operator: str, observed: Any, threshold: Any, previous: Any = None) -> tuple[bool, str]:
    op = str(operator)
    obs_num = _to_float(observed); th_num = _to_float(threshold); prev_num = _to_float(previous)
    if op in {"above", "below", "crosses_above", "crosses_below"} and (obs_num is None or th_num is None):
        return False, "data_gap"
    if op == "above": return bool(obs_num > th_num), "evaluated"
    if op == "below": return bool(obs_num < th_num), "evaluated"
    if op == "crosses_above": return bool(prev_num is not None and prev_num <= th_num and obs_num > th_num), "evaluated"
    if op == "crosses_below": return bool(prev_num is not None and prev_num >= th_num and obs_num < th_num), "evaluated"
    if op == "equals": return str(observed) == str(threshold), "evaluated"
    if op == "not_equals": return str(observed) != str(threshold), "evaluated"
    if op == "contains": return str(threshold).lower() in str(observed).lower(), "evaluated"
    if op == "status_is": return str(observed).lower() == str(threshold).lower(), "evaluated"
    if op == "stale_for": return str(observed).lower() in {"stale", "aging", "missing", "unavailable", "missing-key", "missing_key"}, "evaluated"
    return False, "unsupported"


def _escalate(severity: str, triggered: bool, status: str) -> str:
    if not triggered:
        return severity or "info"
    order = ["info", "watch", "elevated", "high", "critical"]
    sev = severity if severity in order else "watch"
    if status == "data_gap":
        return "watch"
    return sev


def build_alert_event(rule: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    triggered = bool(evaluation.get("triggered"))
    status = evaluation.get("status") or ("triggered" if triggered else "not_triggered")
    event_hash = evaluation.get("event_hash") or build_alert_event_hash(rule, evaluation)
    return {
        "alert_id": rule.get("alert_id", ""),
        "watch_item_id": rule.get("watch_item_id", ""),
        "status": status,
        "triggered": triggered,
        "severity": evaluation.get("severity") or rule.get("severity", "watch"),
        "metric": rule.get("metric", ""),
        "observed_value": str(evaluation.get("observed_value", "")),
        "threshold": str(rule.get("threshold", "")),
        "message": evaluation.get("message") or f"Alert {status}: {rule.get('metric')} {rule.get('operator')} {rule.get('threshold')}",
        "source_snapshot_json": evaluation.get("source_snapshot", {"freshness": "unknown", "confidence": "unknown"}),
        "data_confidence": evaluation.get("data_confidence", "unknown"),
        "metadata_json": {
            "manual_evaluation": True,
            "event_hash": event_hash,
            "previous_observed_value": evaluation.get("previous_observed_value"),
            "observed_value_raw": evaluation.get("observed_value"),
            "transition_type": evaluation.get("transition_type"),
            "dedupe_status": evaluation.get("dedupe_status", "stored"),
            "cooldown_status": evaluation.get("cooldown_status", "not_in_cooldown"),
            "data_gap_reason": evaluation.get("data_gap_reason"),
        },
    }


def evaluate_alert_with_state(rule: dict[str, Any], data_context: dict[str, Any] | None = None, *, persist: bool = False, db_path: str | Path | None = None, store_non_triggered: bool = True) -> dict[str, Any]:
    expiry = apply_alert_expiry(rule)
    if expiry.get("expired"):
        result = {"status": expiry["status"], "triggered": False, "observed_value": None, "message": expiry["message"], "data_confidence": "not_evaluated", "transition_type": "skipped_expired"}
        if persist:
            update_alert_state(rule, result, db_path=db_path)
        return result
    cooldown = apply_alert_cooldown(rule)
    if cooldown.get("in_cooldown"):
        result = {"status": cooldown["status"], "triggered": False, "observed_value": None, "message": cooldown["message"], "data_confidence": "not_evaluated", "cooldown_status": "blocked", "transition_type": "skipped_cooldown"}
        if persist:
            update_alert_state(rule, result, db_path=db_path)
        return result

    resolved = resolve_alert_metric(rule, data_context or {}, db_path=db_path)
    metric = rule.get("metric")
    observed = resolved.get("observed_value")
    previous = (data_context or {}).get(f"previous_{metric}")
    if previous is None:
        previous = get_previous_observed_value(str(rule.get("alert_id")), metric, db_path=db_path)
    if observed is None:
        result = {"status": "skipped_data_gap", "triggered": False, "observed_value": None, "message": f"Missing data for metric {metric}; no false trigger created.", "data_confidence": "missing", "source_snapshot": resolved.get("source_snapshot", {}), "data_gap_reason": f"metric {metric} unavailable", "transition_type": "skipped_data_gap"}
    else:
        triggered, status = _compare(rule.get("operator", "above"), observed, rule.get("threshold"), previous)
        prior_triggered = bool(rule.get("triggered")) if rule.get("triggered") is not None else None
        transition = classify_alert_transition(prior_triggered, triggered, "triggered" if triggered else status)
        result = {"status": "triggered" if triggered else status, "triggered": triggered, "observed_value": observed, "previous_observed_value": previous, "message": "Alert condition matched." if triggered else "Alert condition not matched.", "data_confidence": resolved.get("data_confidence", "unknown"), "source_snapshot": resolved.get("source_snapshot", {}), "transition_type": transition, "severity": _escalate(rule.get("severity", "watch"), triggered, status), "cooldown_status": "not_in_cooldown"}
    dedupe = dedupe_alert_event(rule, result, db_path=db_path) if persist and result.get("triggered") else {"duplicate": False, "dedupe_key": build_alert_event_hash(rule, result)}
    result["event_hash"] = dedupe.get("dedupe_key")
    result["dedupe_status"] = "duplicate" if dedupe.get("duplicate") else "stored"
    if persist:
        should_store = store_non_triggered or bool(result.get("triggered"))
        if result.get("triggered") and dedupe.get("duplicate"):
            should_store = False
        if should_store:
            event = store_alert_event(build_alert_event(rule, result), db_path=db_path)
            result["event"] = event
        update_alert_state(rule, result, db_path=db_path)
    return result


def evaluate_alert_rule(rule: dict[str, Any], data_context: dict[str, Any] | None = None, *, persist: bool = False, db_path: str | Path | None = None) -> dict[str, Any]:
    return evaluate_alert_with_state(rule, data_context, persist=persist, db_path=db_path)


def evaluate_all_alerts(data_context_by_metric: dict[str, Any] | None = None, *, persist: bool = True, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    rules = list_alert_rules(active_only=True, db_path=db_path)
    results = []
    for rule in rules:
        ctx = data_context_by_metric or {}
        if rule.get("watch_item_id") and isinstance(ctx.get(rule["watch_item_id"]), dict):
            ctx = {**ctx, **ctx[rule["watch_item_id"]]}
        results.append(evaluate_alert_with_state(rule, ctx, persist=persist, db_path=db_path))
    return results


def build_alert_evaluation_batch(rules: list[dict[str, Any]], data_context: dict[str, Any] | None = None, *, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    return [evaluate_alert_with_state(rule, data_context or {}, persist=False, db_path=db_path) for rule in rules]


def build_alert_review_queue(db_path: str | Path | None = None, limit: int = 100) -> list[dict[str, Any]]:
    rows = list_alert_events(limit=limit, db_path=db_path)
    severity_rank = {"critical": 5, "high": 4, "elevated": 3, "watch": 2, "info": 1}
    return sorted(rows, key=lambda e: (severity_rank.get(str(e.get("severity")), 0), e.get("created_at", "")), reverse=True)
