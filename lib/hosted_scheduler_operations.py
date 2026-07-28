from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .identity_tenancy import _require_authenticated
from .research_workspace_db import get_connection, json_dumps, json_loads, new_id


HOSTED_SCHEDULER_VERSION = "hosted_scheduler_operations.v1"
HOSTED_SCHEDULER_EVIDENCE_VERSION = "phase6q.hosted.handoff.v1"
RUNNER_KIND = "github-actions-python"
SCHEDULE_STATES = {"disabled", "enabled", "paused", "killed", "deleted"}
RUN_STATUSES = {
    "queued",
    "leased",
    "running",
    "completed",
    "partial",
    "quota-blocked",
    "provider-unavailable",
    "cancelled",
    "killed",
    "failed",
}
TERMINAL_RUN_STATUSES = RUN_STATUSES - {"queued", "leased", "running"}
CADENCE_MINUTES = {60, 240, 1_440}
MAX_SCHEDULES_PER_TENANT = 1
MAX_SCHEDULE_SYMBOLS = 5
MAX_PROVIDER_CALLS = 16
MAX_ATTEMPTS = 3
MIN_TIMEOUT_SECONDS = 15
MAX_TIMEOUT_SECONDS = 120
DEFAULT_LEASE_SECONDS = 120
MAX_RUN_HISTORY = 50
MAX_AUDIT_HISTORY = 100
DEFAULT_EVIDENCE_MAX_AGE_HOURS = 168

HOSTED_EVIDENCE_ASSERTIONS = (
    "deployed_invocation",
    "job_history_observed",
    "tenant_source_backed_result",
    "explainable_trigger",
    "account_isolation",
    "cross_tenant_write_blocked",
    "overlap_suppressed",
    "idempotent_replay",
    "quota_bounded",
    "provider_failure_preserved_lkg",
    "kill_switch",
    "lease_recovery",
    "cleanup",
    "audit_retained",
    "zero_read_provider_calls",
)

_EVIDENCE_PRIVATE_KEYS = {
    "access_token",
    "authorization",
    "cookie",
    "email",
    "headers",
    "password",
    "payload_rows",
    "raw_provider_body",
    "refresh_token",
    "secret",
    "service_role_key",
    "supabase_secret_key",
    "tenant_id",
    "user_id",
}
_EVIDENCE_PRIVATE_PATTERNS = (
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.IGNORECASE),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\bsb_secret_[A-Za-z0-9_-]+\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\b[A-Za-z]:\\(?:[^\s\"']+\\)*[^\s\"']*"),
)

_SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{2,119}$")
_CLIENT_IDENTITY_FIELDS = {
    "tenant_id",
    "owner_user_id",
    "user_id",
    "lease_owner",
    "lease_token",
    "scheduler_run_id",
}
_PRIVATE_KEYS = {
    "access_token",
    "authorization",
    "cookie",
    "csrf_token",
    "lease_token",
    "lease_token_hash",
    "password",
    "private_note",
    "provider_key",
    "refresh_token",
    "secret",
    "service_role_key",
    "supabase_secret_key",
}


class HostedSchedulerConflict(RuntimeError):
    def __init__(self, current_version: int):
        super().__init__("Hosted schedule version conflict.")
        self.current_version = max(0, int(current_version))


class HostedSchedulerLeaseError(RuntimeError):
    pass


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0)


def _iso(value: datetime | str | None = None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _utc(value).isoformat()
    parsed = _parse_time(value)
    return parsed.isoformat() if parsed else None


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _utc(parsed)


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _hash(value: Any) -> str:
    if isinstance(value, str):
        encoded = value.encode("utf-8")
    else:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sanitize(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[depth-limited]"
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item, depth=depth + 1)
            for key, item in value.items()
            if str(key).strip().lower() not in _PRIVATE_KEYS
            and not str(key).strip().lower().endswith("_secret")
            and not str(key).strip().lower().endswith("_token")
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item, depth=depth + 1) for item in list(value)[:100]]
    if isinstance(value, str):
        return value[:4_000]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:1_000]


def normalize_timezone(value: Any) -> str:
    name = str(value or "UTC").strip() or "UTC"
    if len(name) > 64 or not re.fullmatch(r"[A-Za-z0-9_+./-]+", name):
        raise ValueError("Invalid scheduler timezone.")
    try:
        zone = ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unknown scheduler timezone.") from exc
    return str(zone.key)


def calculate_next_due(
    after: datetime,
    cadence_minutes: int,
    *,
    anchor: datetime | None = None,
    timezone_name: str = "UTC",
) -> datetime:
    cadence = int(cadence_minutes)
    if cadence not in CADENCE_MINUTES:
        raise ValueError("Unsupported hosted scheduler cadence.")
    current = _utc(after)
    base = _utc(anchor or current)
    if base > current:
        return base
    if cadence == 1_440:
        zone = ZoneInfo(normalize_timezone(timezone_name))
        local_base = base.astimezone(zone)
        local_current = current.astimezone(zone)
        day_count = max(0, (local_current.date() - local_base.date()).days)
        candidate_date: date = local_base.date() + timedelta(days=day_count)
        wall_clock = time(
            local_base.hour,
            local_base.minute,
            local_base.second,
            tzinfo=zone,
            fold=local_base.fold,
        )
        candidate = datetime.combine(candidate_date, wall_clock)
        if candidate.astimezone(timezone.utc) <= current:
            candidate = datetime.combine(candidate_date + timedelta(days=1), wall_clock)
        return candidate.astimezone(timezone.utc).replace(microsecond=0)
    interval_seconds = cadence * 60
    elapsed = max(0, int((current - base).total_seconds()))
    windows = elapsed // interval_seconds + 1
    return base + timedelta(seconds=windows * interval_seconds)


def localized_due_label(value: datetime | str | None, timezone_name: str) -> str | None:
    parsed = _parse_time(value)
    if not parsed:
        return None
    zone = ZoneInfo(normalize_timezone(timezone_name))
    return parsed.astimezone(zone).replace(microsecond=0).isoformat()


def due_window_idempotency_key(schedule_id: str, due_window_at: datetime | str) -> str:
    due = _iso(due_window_at)
    if not _SAFE_ID.fullmatch(str(schedule_id or "")) or not due:
        raise ValueError("Invalid hosted schedule due window.")
    return f"hosted-schedule-{_hash({'schedule_id': schedule_id, 'due_window_at': due})[:32]}"


def validate_schedule_request(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError("Hosted schedule body must be an object.")
    if _CLIENT_IDENTITY_FIELDS.intersection(body):
        raise ValueError("Hosted schedule identity and lease scope are server-derived.")
    allowed = {
        "watchlist_id",
        "alert_rule_id",
        "timezone",
        "cadence_minutes",
        "max_symbols",
        "max_provider_calls",
        "max_attempts",
        "timeout_seconds",
    }
    if set(body) - allowed:
        raise ValueError("Unsupported hosted schedule field.")
    watchlist_id = str(body.get("watchlist_id") or "").strip()
    alert_rule_id = str(body.get("alert_rule_id") or "").strip()
    if not _SAFE_ID.fullmatch(watchlist_id) or not _SAFE_ID.fullmatch(alert_rule_id):
        raise ValueError("Invalid hosted schedule parent identifier.")
    cadence = int(body.get("cadence_minutes") or 60)
    if cadence not in CADENCE_MINUTES:
        raise ValueError("Hosted schedules support 60, 240, or 1440 minute cadence.")
    max_symbols = int(body.get("max_symbols") or 1)
    max_calls = int(body.get("max_provider_calls") or 4)
    max_attempts = int(body.get("max_attempts") or 2)
    timeout_seconds = int(body.get("timeout_seconds") or 90)
    if not 1 <= max_symbols <= MAX_SCHEDULE_SYMBOLS:
        raise ValueError("max_symbols exceeds the hosted pilot bound.")
    if not 0 <= max_calls <= MAX_PROVIDER_CALLS:
        raise ValueError("max_provider_calls exceeds the hosted pilot bound.")
    if not 1 <= max_attempts <= MAX_ATTEMPTS:
        raise ValueError("max_attempts exceeds the hosted pilot bound.")
    if not MIN_TIMEOUT_SECONDS <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError("timeout_seconds exceeds the hosted pilot bound.")
    return {
        "watchlist_id": watchlist_id,
        "alert_rule_id": alert_rule_id,
        "timezone": normalize_timezone(body.get("timezone")),
        "cadence_minutes": cadence,
        "max_symbols": max_symbols,
        "max_provider_calls": max_calls,
        "max_attempts": max_attempts,
        "timeout_seconds": timeout_seconds,
    }


def _schedule_row(row: Any) -> dict[str, Any]:
    source = dict(row or {})
    timezone_name = str(source.get("timezone") or "UTC")
    return {
        "schedule_id": str(source.get("schedule_id") or ""),
        "watchlist_id": str(source.get("watchlist_resource_id") or ""),
        "alert_rule_id": str(source.get("alert_rule_resource_id") or ""),
        "state": str(source.get("state") or "disabled"),
        "timezone": timezone_name,
        "cadence_minutes": int(source.get("cadence_minutes") or 60),
        "bounds": {
            "max_symbols": int(source.get("max_symbols") or 1),
            "max_provider_calls": int(source.get("max_provider_calls") or 0),
            "max_attempts": int(source.get("max_attempts") or 1),
            "timeout_seconds": int(source.get("timeout_seconds") or 0),
        },
        "next_due_at": source.get("next_due_at"),
        "next_due_local": localized_due_label(source.get("next_due_at"), timezone_name),
        "last_attempted_at": source.get("last_attempted_at"),
        "last_completed_at": source.get("last_completed_at"),
        "last_run_id": source.get("last_run_id"),
        "last_lkg_run_id": source.get("last_lkg_run_id"),
        "consented_at": source.get("consented_at"),
        "enabled_at": source.get("enabled_at"),
        "paused_at": source.get("paused_at"),
        "killed_at": source.get("killed_at"),
        "version": int(source.get("version") or 1),
        "updated_at": source.get("updated_at"),
    }


def _run_row(row: Any) -> dict[str, Any]:
    source = dict(row or {})
    return {
        "scheduler_run_id": str(source.get("scheduler_run_id") or ""),
        "schedule_id": str(source.get("schedule_id") or ""),
        "due_window_at": source.get("due_window_at"),
        "status": str(source.get("status") or "queued"),
        "attempt_count": int(source.get("attempt_count") or 0),
        "lease_acquired_at": source.get("lease_acquired_at"),
        "lease_expires_at": source.get("lease_expires_at"),
        "heartbeat_at": source.get("heartbeat_at"),
        "observation_run_id": source.get("observation_run_id"),
        "evaluation_run_id": source.get("evaluation_run_id"),
        "trigger_count": int(source.get("trigger_count") or 0),
        "quota": {
            "budget": int(source.get("provider_call_budget") or 0),
            "used": int(source.get("provider_call_count") or 0),
            "remaining": max(0, int(source.get("provider_call_budget") or 0) - int(source.get("provider_call_count") or 0)),
        },
        "source": {
            "provider": str(source.get("provider") or ""),
            "source_url": str(source.get("source_url") or ""),
            "source_status": str(source.get("source_status") or "unavailable"),
        },
        "clocks": {
            "observed_at": source.get("observed_at"),
            "retrieved_at": source.get("retrieved_at"),
            "evaluated_at": source.get("evaluated_at"),
            "triggered_at": source.get("triggered_at"),
            "completed_at": source.get("completed_at"),
        },
        "result": _sanitize(
            source.get("result")
            if isinstance(source.get("result"), dict)
            else json_loads(source.get("result_json"), {})
        ),
        "error_code": str(source.get("error_code") or ""),
        "duration_ms": int(source.get("duration_ms") or 0),
        "lkg_run_id": source.get("lkg_run_id"),
        "idempotent_replay": bool(source.get("idempotent_replay")),
    }


def _evidence_private_key_paths(value: Any, *, path: str = "") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            child_path = f"{path}.{normalized}" if path else normalized
            if normalized in _EVIDENCE_PRIVATE_KEYS:
                matches.append(child_path)
            matches.extend(_evidence_private_key_paths(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(_evidence_private_key_paths(child, path=f"{path}[{index}]"))
    return matches


def _evidence_int(value: Any, *, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def validate_hosted_scheduler_evidence(
    payload: Any,
    *,
    now: datetime | None = None,
    max_age_hours: int | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(payload, dict):
        return {
            "passed": False,
            "evidence_version": "",
            "checked_assertion_count": 0,
            "reasons": ["evidence-not-object"],
        }

    if payload.get("evidence_version") != HOSTED_SCHEDULER_EVIDENCE_VERSION:
        reasons.append("evidence-version-mismatch")
    if payload.get("passed") is not True or payload.get("hosted_scheduler_verified") is not True:
        reasons.append("completion-flags-missing")

    current = _utc(now)
    captured = _parse_time(payload.get("captured_at"))
    age_limit = max(1, min(720, _evidence_int(max_age_hours or DEFAULT_EVIDENCE_MAX_AGE_HOURS, default=DEFAULT_EVIDENCE_MAX_AGE_HOURS)))
    if captured is None:
        reasons.append("captured-at-invalid")
    elif captured > current + timedelta(minutes=5):
        reasons.append("captured-at-in-future")
    elif captured < current - timedelta(hours=age_limit):
        reasons.append("evidence-stale")

    runner = payload.get("runner") if isinstance(payload.get("runner"), dict) else {}
    if runner.get("kind") != RUNNER_KIND:
        reasons.append("runner-kind-mismatch")
    for field in ("deployed", "default_branch_workflow", "invocation_observed", "job_history_observed"):
        if runner.get(field) is not True:
            reasons.append(f"runner-{field}-missing")
    if _evidence_int(runner.get("concurrency_limit"), default=0) != 1:
        reasons.append("runner-concurrency-unbounded")
    deadline = _evidence_int(runner.get("deadline_seconds"), default=0)
    if deadline < MIN_TIMEOUT_SECONDS or deadline > 240:
        reasons.append("runner-deadline-unbounded")
    if not str(runner.get("workflow_version") or "").strip():
        reasons.append("runner-version-missing")

    assertions = payload.get("assertions") if isinstance(payload.get("assertions"), dict) else {}
    for field in HOSTED_EVIDENCE_ASSERTIONS:
        if assertions.get(field) is not True:
            reasons.append(f"assertion-{field}-missing")

    counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
    exact_zero_fields = (
        "page_read_provider_calls",
        "overlap_additional_provider_calls",
        "duplicate_runs",
        "duplicate_evaluations",
        "duplicate_triggers",
        "duplicate_audit_effects",
        "cross_tenant_visible_rows",
        "cross_tenant_mutable_rows",
        "cleanup_remaining_temp_rows",
    )
    for field in exact_zero_fields:
        if _evidence_int(counts.get(field), default=-1) != 0 or field not in counts:
            reasons.append(f"count-{field}-not-zero")
    if _evidence_int(counts.get("source_backed_results"), default=0) < 1:
        reasons.append("source-backed-result-missing")
    provider_calls = _evidence_int(counts.get("provider_calls"), default=0)
    if provider_calls < 1 or provider_calls > MAX_PROVIDER_CALLS:
        reasons.append("provider-call-count-invalid")
    if _evidence_int(counts.get("trigger_count"), default=0) < 1:
        reasons.append("trigger-count-missing")
    if _evidence_int(counts.get("job_history_rows"), default=0) < 1:
        reasons.append("job-history-missing")

    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    source_status = str(source.get("source_status") or "").strip().lower()
    blocked_status_parts = {"fixture", "static", "proxy", "unavailable", "missing-key", "configured-unverified"}
    if source.get("source_backed") is not True:
        reasons.append("source-not-backed")
    if not str(source.get("provider") or "").strip():
        reasons.append("source-provider-missing")
    if not str(source.get("source_url") or "").startswith("https://"):
        reasons.append("source-url-invalid")
    if not source_status or any(part in source_status for part in blocked_status_parts):
        reasons.append("source-status-invalid")
    for field in ("retrieved_at", "observed_at"):
        if _parse_time(source.get(field)) is None:
            reasons.append(f"source-{field}-invalid")

    if payload.get("final_schedule_state") not in {"disabled", "enabled-owner-confirmed"}:
        reasons.append("final-schedule-state-unsafe")
    privacy = payload.get("privacy") if isinstance(payload.get("privacy"), dict) else {}
    for field, expected in (
        ("identifiers_redacted", True),
        ("secrets_printed", False),
        ("private_payloads_printed", False),
    ):
        if privacy.get(field) is not expected:
            reasons.append(f"privacy-{field}-invalid")
    if _evidence_private_key_paths(payload):
        reasons.append("private-key-present")
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    if any(pattern.search(encoded) for pattern in _EVIDENCE_PRIVATE_PATTERNS):
        reasons.append("private-value-pattern-present")

    unique_reasons = sorted(set(reasons))
    return {
        "passed": not unique_reasons,
        "evidence_version": str(payload.get("evidence_version") or ""),
        "checked_assertion_count": len(HOSTED_EVIDENCE_ASSERTIONS),
        "max_age_hours": age_limit,
        "reasons": unique_reasons,
    }


def hosted_scheduler_evidence_verified(path: str | Path | None = None) -> bool:
    candidate = str(path or os.getenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_EVIDENCE_PATH") or "").strip()
    if not candidate or not _truthy(os.getenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_VERIFIED")):
        return False
    try:
        payload = json.loads(Path(candidate).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    try:
        max_age_hours = int(os.getenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_EVIDENCE_MAX_AGE_HOURS") or DEFAULT_EVIDENCE_MAX_AGE_HOURS)
    except ValueError:
        return False
    return bool(validate_hosted_scheduler_evidence(payload, max_age_hours=max_age_hours)["passed"])


class HostedSchedulerStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path

    @staticmethod
    def _audit(
        conn: Any,
        tenant_id: str,
        user_id: str,
        schedule_id: str,
        event_type: str,
        prior_state: str,
        new_state: str,
        timestamp: str,
        *,
        scheduler_run_id: str = "",
        detail: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            "INSERT INTO tenant_hosted_observation_schedule_audit (event_id, tenant_id, owner_user_id, schedule_id, scheduler_run_id, event_type, prior_state, new_state, detail_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id("hsaudit"),
                tenant_id,
                user_id,
                schedule_id,
                scheduler_run_id,
                event_type,
                prior_state,
                new_state,
                json_dumps(_sanitize(detail or {})),
                timestamp,
            ),
        )

    def create_schedule(self, context: dict[str, Any], body: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        validated = validate_schedule_request(body)
        timestamp = _utc(now).isoformat()
        with get_connection(self.db_path) as conn:
            watchlist = conn.execute(
                "SELECT resource_id FROM tenant_watchlists WHERE tenant_id=? AND resource_id=? AND active=1",
                (tenant_id, validated["watchlist_id"]),
            ).fetchone()
            if not watchlist:
                raise KeyError("Saved Watchlist not found.")
            rule = conn.execute(
                "SELECT resource_id, watchlist_resource_id, state FROM tenant_watchlist_alert_rules WHERE tenant_id=? AND resource_id=? AND state!='deleted'",
                (tenant_id, validated["alert_rule_id"]),
            ).fetchone()
            if not rule or str(rule["watchlist_resource_id"]) != validated["watchlist_id"]:
                raise KeyError("Hosted schedule alert policy not found for this Watchlist.")
            count = conn.execute(
                "SELECT COUNT(*) FROM tenant_hosted_observation_schedules WHERE tenant_id=? AND state!='deleted'",
                (tenant_id,),
            ).fetchone()[0]
            if int(count) >= MAX_SCHEDULES_PER_TENANT:
                raise ValueError("The hosted pilot supports one schedule per account.")
            schedule_id = new_id("hsched")
            conn.execute(
                """
                INSERT INTO tenant_hosted_observation_schedules (
                    schedule_id, tenant_id, owner_user_id, watchlist_resource_id,
                    alert_rule_resource_id, state, timezone, cadence_minutes,
                    max_symbols, max_provider_calls, max_attempts, timeout_seconds,
                    version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'disabled', ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    schedule_id,
                    tenant_id,
                    user_id,
                    validated["watchlist_id"],
                    validated["alert_rule_id"],
                    validated["timezone"],
                    validated["cadence_minutes"],
                    validated["max_symbols"],
                    validated["max_provider_calls"],
                    validated["max_attempts"],
                    validated["timeout_seconds"],
                    timestamp,
                    timestamp,
                ),
            )
            self._audit(conn, tenant_id, user_id, schedule_id, "schedule-created", "", "disabled", timestamp)
            row = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedules WHERE schedule_id=?",
                (schedule_id,),
            ).fetchone()
        return _schedule_row(row)

    def get_schedule(self, context: dict[str, Any], schedule_id: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedules WHERE tenant_id=? AND schedule_id=? AND state!='deleted'",
                (tenant_id, str(schedule_id)),
            ).fetchone()
        return _schedule_row(row) if row else None

    def list_schedules(self, context: dict[str, Any], *, include_deleted: bool = False) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        where = "" if include_deleted else "AND state!='deleted'"
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT * FROM tenant_hosted_observation_schedules WHERE tenant_id=? {where} ORDER BY updated_at DESC, schedule_id",
                (tenant_id,),
            ).fetchall()
        return [_schedule_row(row) for row in rows]

    def update_schedule(
        self,
        context: dict[str, Any],
        schedule_id: str,
        body: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        if not isinstance(body, dict) or _CLIENT_IDENTITY_FIELDS.intersection(body):
            raise ValueError("Hosted schedule identity is server-derived.")
        if set(body) - {"action", "expected_version", "consent"}:
            raise ValueError("Unsupported hosted schedule action field.")
        action = str(body.get("action") or "").strip().lower()
        if action not in {"enable", "pause", "resume", "kill", "recover", "retry", "delete"}:
            raise ValueError("Unsupported hosted schedule action.")
        expected_version = body.get("expected_version")
        if not isinstance(expected_version, int) or expected_version < 1:
            raise ValueError("expected_version must be a positive integer.")
        if action in {"enable", "recover"} and body.get("consent") is not True:
            raise ValueError("Explicit hosted schedule consent is required.")
        current = _utc(now)
        timestamp = current.isoformat()
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedules WHERE tenant_id=? AND schedule_id=?",
                (tenant_id, str(schedule_id)),
            ).fetchone()
            if not row:
                raise KeyError("Hosted schedule not found.")
            existing = dict(row)
            if int(existing.get("version") or 0) != expected_version:
                raise HostedSchedulerConflict(int(existing.get("version") or 0))
            prior = str(existing.get("state") or "disabled")
            target = prior
            next_due = existing.get("next_due_at")
            consented_at = existing.get("consented_at")
            enabled_at = existing.get("enabled_at")
            paused_at = existing.get("paused_at")
            killed_at = existing.get("killed_at")
            deleted_at = existing.get("deleted_at")
            if action in {"enable", "resume"}:
                if prior not in {"disabled", "paused"}:
                    raise ValueError("Hosted schedule cannot be enabled from its current state.")
                target = "enabled"
                next_due = timestamp
                enabled_at = timestamp
                consented_at = consented_at or timestamp
            elif action == "pause":
                if prior != "enabled":
                    raise ValueError("Only an enabled hosted schedule can be paused.")
                target = "paused"
                next_due = None
                paused_at = timestamp
            elif action == "kill":
                if prior in {"deleted", "killed"}:
                    raise ValueError("Hosted schedule is already stopped.")
                target = "killed"
                next_due = None
                killed_at = timestamp
            elif action == "recover":
                if prior != "killed":
                    raise ValueError("Only a killed hosted schedule can enter recovery.")
                target = "paused"
                next_due = None
                consented_at = timestamp
                paused_at = timestamp
            elif action == "retry":
                if prior != "enabled":
                    raise ValueError("Only an enabled hosted schedule can retry.")
                next_due = timestamp
            elif action == "delete":
                if prior == "enabled":
                    raise ValueError("Pause or kill the hosted schedule before deletion.")
                target = "deleted"
                next_due = None
                deleted_at = timestamp
            conn.execute(
                """
                UPDATE tenant_hosted_observation_schedules
                   SET state=?, next_due_at=?, consented_at=?, enabled_at=?,
                       paused_at=?, killed_at=?, deleted_at=?, version=version+1,
                       updated_at=?
                 WHERE tenant_id=? AND schedule_id=?
                """,
                (
                    target,
                    next_due,
                    consented_at,
                    enabled_at,
                    paused_at,
                    killed_at,
                    deleted_at,
                    timestamp,
                    tenant_id,
                    schedule_id,
                ),
            )
            self._audit(
                conn,
                tenant_id,
                user_id,
                schedule_id,
                f"schedule-{action}",
                prior,
                target,
                timestamp,
                detail={"version": expected_version + 1},
            )
            updated = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedules WHERE schedule_id=?",
                (schedule_id,),
            ).fetchone()
        return _schedule_row(updated)

    def claim_due(
        self,
        worker_id: str,
        *,
        now: datetime | None = None,
        operator_enabled: bool = False,
        global_kill: bool = True,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> dict[str, Any]:
        worker = str(worker_id or "").strip()
        if not _SAFE_ID.fullmatch(worker):
            raise ValueError("Invalid scheduler worker identifier.")
        if not operator_enabled:
            return {"claimed": False, "status": "disabled", "reason": "operator-gate-disabled", "provider_call_count": 0}
        if global_kill:
            return {"claimed": False, "status": "killed", "reason": "global-kill-switch", "provider_call_count": 0}
        current = _utc(now)
        timestamp = current.isoformat()
        bounded_lease = max(30, min(int(lease_seconds), 300))
        lease_expiry = (current + timedelta(seconds=bounded_lease)).isoformat()
        worker_hash = _hash(worker)
        lease_token = secrets.token_urlsafe(32)
        token_hash = _hash(lease_token)
        with get_connection(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            schedule = conn.execute(
                """
                SELECT * FROM tenant_hosted_observation_schedules schedule
                 WHERE schedule.state='enabled'
                   AND schedule.next_due_at IS NOT NULL
                   AND schedule.next_due_at<=?
                 ORDER BY schedule.next_due_at, schedule.schedule_id
                 LIMIT 1
                """,
                (timestamp,),
            ).fetchone()
            if not schedule:
                return {"claimed": False, "status": "no-due", "reason": "no-enabled-due-schedule", "provider_call_count": 0}
            schedule_row = dict(schedule)
            due_window = str(schedule_row["next_due_at"])
            existing = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedule_runs WHERE tenant_id=? AND schedule_id=? AND due_window_at=?",
                (schedule_row["tenant_id"], schedule_row["schedule_id"], due_window),
            ).fetchone()
            if existing:
                run = dict(existing)
                status = str(run.get("status") or "queued")
                expiry = _parse_time(run.get("lease_expires_at"))
                if status in TERMINAL_RUN_STATUSES:
                    return {"claimed": False, "status": status, "reason": "idempotent-window-complete", "idempotent_replay": True, "provider_call_count": 0}
                if expiry and expiry > current:
                    return {"claimed": False, "status": "overlap", "reason": "lease-active", "provider_call_count": 0}
                if int(run.get("attempt_count") or 0) >= int(schedule_row.get("max_attempts") or 1):
                    conn.execute(
                        "UPDATE tenant_hosted_observation_schedule_runs SET status='failed', error_code='lease-attempts-exhausted', completed_at=?, updated_at=? WHERE scheduler_run_id=?",
                        (timestamp, timestamp, run["scheduler_run_id"]),
                    )
                    self._audit(
                        conn,
                        str(schedule_row["tenant_id"]),
                        str(schedule_row["owner_user_id"]),
                        str(schedule_row["schedule_id"]),
                        "run-lease-exhausted",
                        status,
                        "failed",
                        timestamp,
                        scheduler_run_id=str(run["scheduler_run_id"]),
                    )
                    next_due = calculate_next_due(
                        current,
                        int(schedule_row["cadence_minutes"]),
                        anchor=_parse_time(due_window),
                        timezone_name=str(schedule_row.get("timezone") or "UTC"),
                    ).isoformat()
                    conn.execute(
                        "UPDATE tenant_hosted_observation_schedules SET next_due_at=?, last_attempted_at=?, last_run_id=?, updated_at=? WHERE schedule_id=?",
                        (next_due, timestamp, run["scheduler_run_id"], timestamp, schedule_row["schedule_id"]),
                    )
                    return {"claimed": False, "status": "failed", "reason": "lease-attempts-exhausted", "provider_call_count": 0}
                run_id = str(run["scheduler_run_id"])
                attempt = int(run.get("attempt_count") or 0) + 1
                conn.execute(
                    """
                    UPDATE tenant_hosted_observation_schedule_runs
                       SET status='leased', lease_owner_hash=?, lease_token_hash=?,
                           lease_acquired_at=?, lease_expires_at=?, heartbeat_at=?,
                           attempt_count=?, error_code='', updated_at=?
                     WHERE scheduler_run_id=?
                    """,
                    (worker_hash, token_hash, timestamp, lease_expiry, timestamp, attempt, timestamp, run_id),
                )
                prior = status
            else:
                run_id = new_id("hsrun")
                attempt = 1
                prior = ""
                conn.execute(
                    """
                    INSERT INTO tenant_hosted_observation_schedule_runs (
                        scheduler_run_id, tenant_id, owner_user_id, schedule_id,
                        due_window_at, idempotency_key, status, lease_owner_hash,
                        lease_token_hash, lease_acquired_at, lease_expires_at,
                        heartbeat_at, attempt_count, provider_call_budget,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'leased', ?, ?, ?, ?, ?, 1, ?, ?, ?)
                    """,
                    (
                        run_id,
                        schedule_row["tenant_id"],
                        schedule_row["owner_user_id"],
                        schedule_row["schedule_id"],
                        due_window,
                        due_window_idempotency_key(str(schedule_row["schedule_id"]), due_window),
                        worker_hash,
                        token_hash,
                        timestamp,
                        lease_expiry,
                        timestamp,
                        int(schedule_row["max_provider_calls"]),
                        timestamp,
                        timestamp,
                    ),
                )
            conn.execute(
                "UPDATE tenant_hosted_observation_schedules SET last_attempted_at=?, last_run_id=?, updated_at=? WHERE schedule_id=?",
                (timestamp, run_id, timestamp, schedule_row["schedule_id"]),
            )
            self._audit(
                conn,
                str(schedule_row["tenant_id"]),
                str(schedule_row["owner_user_id"]),
                str(schedule_row["schedule_id"]),
                "run-leased",
                prior,
                "leased",
                timestamp,
                scheduler_run_id=run_id,
                detail={"attempt": attempt, "lease_seconds": bounded_lease},
            )
        return {
            "claimed": True,
            "status": "leased",
            "scheduler_run_id": run_id,
            "schedule_id": str(schedule_row["schedule_id"]),
            "tenant_id": str(schedule_row["tenant_id"]),
            "owner_user_id": str(schedule_row["owner_user_id"]),
            "watchlist_id": str(schedule_row["watchlist_resource_id"]),
            "alert_rule_id": str(schedule_row["alert_rule_resource_id"]),
            "due_window_at": due_window,
            "lease_expires_at": lease_expiry,
            "lease_token": lease_token,
            "attempt_count": attempt,
            "bounds": {
                "max_symbols": int(schedule_row["max_symbols"]),
                "max_provider_calls": int(schedule_row["max_provider_calls"]),
                "max_attempts": int(schedule_row["max_attempts"]),
                "timeout_seconds": int(schedule_row["timeout_seconds"]),
            },
            "provider_call_count": 0,
        }

    @staticmethod
    def _verify_lease(row: dict[str, Any], lease_token: str, current: datetime) -> None:
        if not lease_token or not secrets.compare_digest(str(row.get("lease_token_hash") or ""), _hash(lease_token)):
            raise HostedSchedulerLeaseError("Hosted scheduler lease was not verified.")
        expiry = _parse_time(row.get("lease_expires_at"))
        if not expiry or expiry <= current:
            raise HostedSchedulerLeaseError("Hosted scheduler lease expired.")

    def mark_running(self, claim: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        current = _utc(now)
        timestamp = current.isoformat()
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedule_runs WHERE scheduler_run_id=?",
                (str(claim.get("scheduler_run_id") or ""),),
            ).fetchone()
            if not row:
                raise KeyError("Hosted scheduler run not found.")
            source = dict(row)
            self._verify_lease(source, str(claim.get("lease_token") or ""), current)
            if source["status"] not in {"leased", "running"}:
                raise HostedSchedulerLeaseError("Hosted scheduler run is not active.")
            conn.execute(
                "UPDATE tenant_hosted_observation_schedule_runs SET status='running', heartbeat_at=?, updated_at=? WHERE scheduler_run_id=?",
                (timestamp, timestamp, source["scheduler_run_id"]),
            )
            self._audit(
                conn,
                str(source["tenant_id"]),
                str(source["owner_user_id"]),
                str(source["schedule_id"]),
                "run-started",
                str(source["status"]),
                "running",
                timestamp,
                scheduler_run_id=str(source["scheduler_run_id"]),
            )
            updated = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedule_runs WHERE scheduler_run_id=?",
                (source["scheduler_run_id"],),
            ).fetchone()
        return _run_row(updated)

    def heartbeat(self, claim: dict[str, Any], *, now: datetime | None = None, extend_seconds: int = DEFAULT_LEASE_SECONDS) -> dict[str, Any]:
        current = _utc(now)
        timestamp = current.isoformat()
        expiry = (current + timedelta(seconds=max(30, min(int(extend_seconds), 300)))).isoformat()
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedule_runs WHERE scheduler_run_id=?",
                (str(claim.get("scheduler_run_id") or ""),),
            ).fetchone()
            if not row:
                raise KeyError("Hosted scheduler run not found.")
            source = dict(row)
            self._verify_lease(source, str(claim.get("lease_token") or ""), current)
            if source["status"] not in {"leased", "running"}:
                raise HostedSchedulerLeaseError("Hosted scheduler run is not active.")
            conn.execute(
                "UPDATE tenant_hosted_observation_schedule_runs SET heartbeat_at=?, lease_expires_at=?, updated_at=? WHERE scheduler_run_id=?",
                (timestamp, expiry, timestamp, source["scheduler_run_id"]),
            )
            updated = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedule_runs WHERE scheduler_run_id=?",
                (source["scheduler_run_id"],),
            ).fetchone()
        return _run_row(updated)

    def finish_run(
        self,
        claim: dict[str, Any],
        result: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise ValueError("Hosted scheduler result must be an object.")
        requested_status = str(result.get("status") or "failed").strip().lower()
        if requested_status not in TERMINAL_RUN_STATUSES:
            raise ValueError("Hosted scheduler result is not terminal.")
        current = _utc(now)
        timestamp = current.isoformat()
        with get_connection(self.db_path) as conn:
            run = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedule_runs WHERE scheduler_run_id=?",
                (str(claim.get("scheduler_run_id") or ""),),
            ).fetchone()
            if not run:
                raise KeyError("Hosted scheduler run not found.")
            run_row = dict(run)
            if str(run_row.get("status") or "") in TERMINAL_RUN_STATUSES:
                replay = _run_row(run_row)
                replay["idempotent_replay"] = True
                return replay
            self._verify_lease(run_row, str(claim.get("lease_token") or ""), current)
            schedule = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedules WHERE schedule_id=?",
                (run_row["schedule_id"],),
            ).fetchone()
            if not schedule:
                raise KeyError("Hosted schedule not found.")
            schedule_row = dict(schedule)
            final_status = "killed" if schedule_row.get("state") == "killed" else requested_status
            provider_calls = max(0, int(result.get("provider_call_count") or 0))
            budget = int(run_row.get("provider_call_budget") or 0)
            if provider_calls > budget:
                raise ValueError("Hosted scheduler provider call count exceeds its lease budget.")
            source_status = str(result.get("source_status") or "unavailable")[:64]
            valid_lkg = final_status in {"completed", "partial"} and source_status not in {"", "unavailable", "provider-error", "malformed"}
            next_due = None
            if schedule_row.get("state") == "enabled":
                anchor = _parse_time(run_row.get("due_window_at")) or current
                next_due = calculate_next_due(
                    current,
                    int(schedule_row["cadence_minutes"]),
                    anchor=anchor,
                    timezone_name=str(schedule_row.get("timezone") or "UTC"),
                ).isoformat()
            started = _parse_time(run_row.get("lease_acquired_at")) or current
            duration_ms = max(0, min(int(result.get("duration_ms") or (current - started).total_seconds() * 1_000), 300_000))
            public_result = _sanitize(
                {
                    "status": final_status,
                    "trigger_count": max(0, int(result.get("trigger_count") or 0)),
                    "caveat": str(result.get("caveat") or "")[:1_000],
                    "data_gap": str(result.get("data_gap") or "")[:1_000],
                    "duplicate_suppressed": bool(result.get("duplicate_suppressed")),
                }
            )
            conn.execute(
                """
                UPDATE tenant_hosted_observation_schedule_runs
                   SET status=?, lease_owner_hash='', lease_token_hash='',
                       heartbeat_at=?, observation_run_id=?, evaluation_run_id=?,
                       trigger_count=?, provider_call_count=?, provider=?, source_url=?,
                       source_status=?, observed_at=?, retrieved_at=?, evaluated_at=?,
                       triggered_at=?, result_json=?, error_code=?, duration_ms=?,
                       lkg_run_id=?, completed_at=?, updated_at=?
                 WHERE scheduler_run_id=?
                """,
                (
                    final_status,
                    timestamp,
                    str(result.get("observation_run_id") or "") or None,
                    str(result.get("evaluation_run_id") or "") or None,
                    max(0, int(result.get("trigger_count") or 0)),
                    provider_calls,
                    str(result.get("provider") or "")[:80],
                    str(result.get("source_url") or "")[:2_000],
                    source_status,
                    _iso(result.get("observed_at")),
                    _iso(result.get("retrieved_at")),
                    _iso(result.get("evaluated_at")),
                    _iso(result.get("triggered_at")),
                    json_dumps(public_result),
                    str(result.get("error_code") or "")[:80],
                    duration_ms,
                    run_row["scheduler_run_id"] if valid_lkg else schedule_row.get("last_lkg_run_id"),
                    timestamp,
                    timestamp,
                    run_row["scheduler_run_id"],
                ),
            )
            conn.execute(
                """
                UPDATE tenant_hosted_observation_schedules
                   SET next_due_at=?, last_attempted_at=?,
                       last_completed_at=CASE WHEN ? IN ('completed','partial') THEN ? ELSE last_completed_at END,
                       last_run_id=?,
                       last_lkg_run_id=CASE WHEN ? THEN ? ELSE last_lkg_run_id END,
                       updated_at=?
                 WHERE schedule_id=?
                """,
                (
                    next_due,
                    timestamp,
                    final_status,
                    timestamp,
                    run_row["scheduler_run_id"],
                    1 if valid_lkg else 0,
                    run_row["scheduler_run_id"],
                    timestamp,
                    run_row["schedule_id"],
                ),
            )
            self._audit(
                conn,
                str(run_row["tenant_id"]),
                str(run_row["owner_user_id"]),
                str(run_row["schedule_id"]),
                "run-finished",
                str(run_row["status"]),
                final_status,
                timestamp,
                scheduler_run_id=str(run_row["scheduler_run_id"]),
                detail={
                    "attempt_count": int(run_row.get("attempt_count") or 0),
                    "provider_call_count": provider_calls,
                    "trigger_count": max(0, int(result.get("trigger_count") or 0)),
                    "source_status": source_status,
                },
            )
            updated = conn.execute(
                "SELECT * FROM tenant_hosted_observation_schedule_runs WHERE scheduler_run_id=?",
                (run_row["scheduler_run_id"],),
            ).fetchone()
        return _run_row(updated)

    def list_runs(self, context: dict[str, Any], *, schedule_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        bounded = max(1, min(int(limit), MAX_RUN_HISTORY))
        with get_connection(self.db_path) as conn:
            if schedule_id:
                rows = conn.execute(
                    "SELECT * FROM tenant_hosted_observation_schedule_runs WHERE tenant_id=? AND schedule_id=? ORDER BY created_at DESC LIMIT ?",
                    (tenant_id, str(schedule_id), bounded),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tenant_hosted_observation_schedule_runs WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
                    (tenant_id, bounded),
                ).fetchall()
        return [_run_row(row) for row in rows]

    def list_audit(self, context: dict[str, Any], *, limit: int = 50) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        bounded = max(1, min(int(limit), MAX_AUDIT_HISTORY))
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT event_id, schedule_id, scheduler_run_id, event_type, prior_state, new_state, detail_json, created_at FROM tenant_hosted_observation_schedule_audit WHERE tenant_id=? ORDER BY created_at DESC, event_id DESC LIMIT ?",
                (tenant_id, bounded),
            ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "schedule_id": row["schedule_id"],
                "scheduler_run_id": row["scheduler_run_id"],
                "event_type": row["event_type"],
                "prior_state": row["prior_state"],
                "new_state": row["new_state"],
                "detail": _sanitize(json_loads(row["detail_json"], {})),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def build_contract(self, context: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        schedules = self.list_schedules(context)
        runs = self.list_runs(context, limit=20)
        audit = self.list_audit(context, limit=20)
        operator_enabled = _truthy(os.getenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_ENABLED"))
        global_kill = _truthy(os.getenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_KILL_SWITCH", "true"))
        verified = hosted_scheduler_evidence_verified()
        latest = runs[0] if runs else None
        lkg = next((row for row in runs if row.get("scheduler_run_id") == (schedules[0].get("last_lkg_run_id") if schedules else None)), None)
        status = "verified" if verified else "disabled" if not operator_enabled or global_kill else "hosted-unverified"
        return {
            "contract_version": HOSTED_SCHEDULER_VERSION,
            "runner": {
                "kind": RUNNER_KIND,
                "cadence_floor_minutes": 60,
                "maximum_concurrency": 1,
                "at_least_once": True,
                "exactly_once_claimed": False,
            },
            "readiness": {
                "status": status,
                "hosted_scheduler_verified": verified,
                "operator_enabled": operator_enabled,
                "global_kill_switch": global_kill,
                "configured_is_not_verified": True,
            },
            "schedules": schedules,
            "runs": runs,
            "audit": audit,
            "latest_run": latest,
            "last_known_good": lkg,
            "summary": {
                "status": status,
                "schedule_count": len(schedules),
                "enabled_count": sum(row.get("state") == "enabled" for row in schedules),
                "active_run_count": sum(row.get("status") in {"leased", "running"} for row in runs),
                "completed_run_count": sum(row.get("status") in {"completed", "partial"} for row in runs),
                "provider_call_count": 0,
            },
            "state_catalog": [
                "disabled",
                "hosted-unverified",
                "enabled",
                "no-due",
                "leased",
                "running",
                "completed",
                "idempotent-replay",
                "quota-blocked",
                "provider-unavailable",
                "partial-lkg",
                "killed",
                "lease-expired",
                "recovered",
                "conflict",
                "session-expired",
            ],
            "generated_at": _utc(now).isoformat(),
            "caveat": "GitHub scheduled workflows can be delayed or dropped. Hosted monitoring remains unverified until the owner handoff records a real deployed invocation.",
            "data_gap": "No hosted recurring schedule evidence is available." if not verified else "",
            "provider_call_count": 0,
            "not_financial_advice": True,
        }


def build_fixture_hosted_scheduler_contract(state: str = "completed") -> dict[str, Any]:
    generated = "2026-07-27T06:17:42+00:00"
    final_state = state if state in {"disabled", "hosted-unverified", "leased", "running", "completed", "quota-blocked", "provider-unavailable", "partial", "killed"} else "completed"
    schedule_state = "killed" if final_state == "killed" else "enabled" if final_state not in {"disabled", "hosted-unverified"} else "disabled"
    run_status = "partial" if final_state == "partial" else final_state
    has_run = run_status not in {"disabled", "hosted-unverified"}
    source_status = "live/fresh" if run_status == "completed" else "stale" if run_status == "partial" else "unavailable"
    run = {
        "scheduler_run_id": "fixture-hosted-run",
        "schedule_id": "fixture-hosted-schedule",
        "due_window_at": "2026-07-27T06:17:00+00:00",
        "status": run_status,
        "attempt_count": 1,
        "lease_acquired_at": "2026-07-27T06:17:02+00:00",
        "lease_expires_at": "2026-07-27T06:19:02+00:00",
        "heartbeat_at": "2026-07-27T06:17:30+00:00",
        "observation_run_id": "fixture-observation-run" if run_status in {"completed", "partial"} else None,
        "evaluation_run_id": "fixture-alert-evaluation" if run_status in {"completed", "partial"} else None,
        "trigger_count": 1 if run_status == "completed" else 0,
        "quota": {"budget": 4, "used": 1 if run_status in {"completed", "partial"} else 0, "remaining": 3 if run_status in {"completed", "partial"} else 4},
        "source": {"provider": "fixture-provider", "source_url": "https://example.test/phase6q", "source_status": source_status},
        "clocks": {"observed_at": "2026-07-27T06:16:00+00:00", "retrieved_at": "2026-07-27T06:17:20+00:00", "evaluated_at": "2026-07-27T06:17:35+00:00", "triggered_at": "2026-07-27T06:17:36+00:00", "completed_at": generated},
        "result": {"status": run_status, "caveat": "Deterministic fixture; no hosted runner or provider was contacted.", "data_gap": "Hosted deployment evidence is unavailable."},
        "error_code": "provider-unavailable" if run_status == "provider-unavailable" else "",
        "duration_ms": 40_000,
        "lkg_run_id": "fixture-hosted-run" if run_status in {"completed", "partial"} else None,
        "idempotent_replay": False,
    }
    schedule = {
        "schedule_id": "fixture-hosted-schedule",
        "watchlist_id": "fixture-daily",
        "alert_rule_id": "fixture-alert-rule-aapl",
        "state": schedule_state,
        "timezone": "Asia/Seoul",
        "cadence_minutes": 60,
        "bounds": {"max_symbols": 1, "max_provider_calls": 4, "max_attempts": 2, "timeout_seconds": 90},
        "next_due_at": "2026-07-27T07:17:00+00:00" if schedule_state == "enabled" else None,
        "next_due_local": "2026-07-27T16:17:00+09:00" if schedule_state == "enabled" else None,
        "last_attempted_at": generated if has_run else None,
        "last_completed_at": generated if run_status in {"completed", "partial"} else None,
        "last_run_id": "fixture-hosted-run" if has_run else None,
        "last_lkg_run_id": "fixture-hosted-run" if run_status in {"completed", "partial"} else None,
        "consented_at": "2026-07-27T05:30:00+00:00",
        "enabled_at": "2026-07-27T05:30:00+00:00" if schedule_state == "enabled" else None,
        "paused_at": None,
        "killed_at": generated if schedule_state == "killed" else None,
        "version": 2,
        "updated_at": generated,
    }
    return {
        "contract_version": HOSTED_SCHEDULER_VERSION,
        "runner": {"kind": RUNNER_KIND, "cadence_floor_minutes": 60, "maximum_concurrency": 1, "at_least_once": True, "exactly_once_claimed": False},
        "readiness": {"status": "hosted-unverified", "hosted_scheduler_verified": False, "operator_enabled": False, "global_kill_switch": True, "configured_is_not_verified": True},
        "schedules": [schedule],
        "runs": [run] if has_run else [],
        "audit": [],
        "latest_run": run if has_run else None,
        "last_known_good": run if run_status in {"completed", "partial"} else None,
        "summary": {"status": final_state, "schedule_count": 1, "enabled_count": 1 if schedule_state == "enabled" else 0, "active_run_count": 1 if run_status in {"leased", "running"} else 0, "completed_run_count": 1 if run_status in {"completed", "partial"} else 0, "provider_call_count": 0},
        "state_catalog": ["disabled", "hosted-unverified", "enabled", "no-due", "leased", "running", "completed", "idempotent-replay", "quota-blocked", "provider-unavailable", "partial-lkg", "killed", "lease-expired", "recovered", "conflict", "session-expired"],
        "generated_at": generated,
        "caveat": "Deterministic fixture; no hosted runner or provider was contacted.",
        "data_gap": "Hosted deployment evidence is unavailable.",
        "provider_call_count": 0,
        "not_financial_advice": True,
    }


def merge_hosted_scheduler_repository_rows(
    contract: dict[str, Any],
    hosted_rows: dict[str, Any],
) -> dict[str, Any]:
    """Overlay RLS-filtered hosted rows without exposing identity or lease proof."""
    output = dict(contract or {})
    schedules = [
        _schedule_row(row)
        for row in list((hosted_rows or {}).get("schedules") or [])[:5]
        if isinstance(row, dict)
    ]
    runs = [
        _run_row(row)
        for row in list((hosted_rows or {}).get("runs") or [])[:20]
        if isinstance(row, dict)
    ]
    if schedules:
        output["schedules"] = schedules
    if runs:
        output["runs"] = runs
    effective_schedules = list(output.get("schedules") or [])
    effective_runs = list(output.get("runs") or [])
    output["latest_run"] = effective_runs[0] if effective_runs else None
    lkg_id = effective_schedules[0].get("last_lkg_run_id") if effective_schedules else None
    output["last_known_good"] = next(
        (row for row in effective_runs if row.get("scheduler_run_id") == lkg_id),
        None,
    )
    summary = dict(output.get("summary") or {})
    summary.update(
        {
            "schedule_count": len(effective_schedules),
            "enabled_count": sum(row.get("state") == "enabled" for row in effective_schedules),
            "active_run_count": sum(row.get("status") in {"leased", "running"} for row in effective_runs),
            "completed_run_count": sum(row.get("status") in {"completed", "partial"} for row in effective_runs),
            "provider_call_count": 0,
        }
    )
    output["summary"] = summary
    output["hosted_repository"] = {
        "contacted": True,
        "source_status": "hosted-rows-visible",
        "schedule_row_count": len(schedules),
        "run_row_count": len(runs),
        "provider_call_count": 0,
        "configured_is_not_verified": True,
    }
    return output
