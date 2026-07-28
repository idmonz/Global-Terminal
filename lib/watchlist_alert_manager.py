from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .alert_evaluator import evaluate_alert_rule
from .identity_tenancy import _require_authenticated, public_account_payload
from .research_workspace_db import execute_query, get_connection, json_dumps, json_loads, new_id


CONTRACT_VERSION = "watchlist_alert_manager.v1"
MAX_ALERT_RULES = 50
MAX_ALERT_TRIGGERS = 250
MAX_ALERT_RUNS = 100
MAX_ALERT_AUDIT_ROWS = 250
FREQUENCIES = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1_440}
SESSION_POLICIES = {"market-aware", "regular-only", "extended", "continuous"}
RULE_STATES = {"active", "paused", "expired", "cancelled", "deleted"}
SEVERITIES = {"info", "watch", "material", "high", "critical"}
DEGRADED_STATUS_RANK = {
    "live/fresh": 0,
    "fresh": 0,
    "cached": 1,
    "aging": 2,
    "stale": 2,
    "partial": 2,
    "rate-limited": 3,
    "forbidden": 3,
    "missing-key": 4,
    "missing_key": 4,
    "error": 4,
    "failed": 4,
    "unavailable": 4,
    "missing": 4,
}
BLOCKED_MARKET_STATUSES = {
    "aging", "stale", "partial", "rate-limited", "forbidden", "missing-key",
    "missing_key", "error", "failed", "unavailable", "missing",
}
RULE_DEFINITIONS = {
    "price_above": {"metric": "last_price", "operator": "above", "unit_kind": "currency"},
    "price_below": {"metric": "last_price", "operator": "below", "unit_kind": "currency"},
    "absolute_percent_move": {"metric": "absolute_change_pct", "operator": "above", "unit_kind": "percent"},
    "material_saved_change": {"metric": "material_change_rank", "operator": "at_or_above", "unit_kind": "severity"},
    "source_degradation": {"metric": "source_status", "operator": "degrades_to_or_below", "unit_kind": "status"},
}
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{3,80}$")
_SAFE_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.=^/_-]{0,31}$")
_SAFE_IDEMPOTENCY = re.compile(r"^[A-Za-z0-9_.:-]{8,128}$")
_CLIENT_IDENTITY_FIELDS = {"tenant_id", "owner_user_id", "user_id"}
_EXTERNAL_DELIVERY_FIELDS = {"webhook", "webhook_url", "email", "phone", "sms", "push", "notification_url"}


class AlertManagerConflict(RuntimeError):
    def __init__(self, current_version: int):
        super().__init__("Alert resource version conflict.")
        self.current_version = int(current_version)


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    return current if current.tzinfo else current.replace(tzinfo=timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return _utc(value).replace(microsecond=0).isoformat()


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_scalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _finite_number(value: Any, *, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite.")
    return number


def _normalize_source_status(value: Any) -> str:
    return str(value or "unavailable").strip().lower().replace(" ", "-")


def validate_alert_rule_request(body: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError("Alert rule body must be an object.")
    if _CLIENT_IDENTITY_FIELDS.intersection(body):
        raise ValueError("Tenant and user identity are server-derived.")
    if _EXTERNAL_DELIVERY_FIELDS.intersection(body):
        raise ValueError("External alert delivery is unavailable in Phase 6O.")
    watchlist_id = str(body.get("watchlist_id") or "").strip()
    if not _SAFE_ID.fullmatch(watchlist_id):
        raise ValueError("Invalid Watchlist identifier.")
    symbol = str(body.get("symbol") or "").strip().upper()
    if not _SAFE_SYMBOL.fullmatch(symbol):
        raise ValueError("Invalid alert symbol.")
    rule_type = str(body.get("rule_type") or "").strip().lower()
    definition = RULE_DEFINITIONS.get(rule_type)
    if not definition:
        raise ValueError("Unsupported alert rule type.")
    frequency = str(body.get("frequency") or "15m").strip().lower()
    if frequency not in FREQUENCIES:
        raise ValueError("Unsupported alert frequency.")
    session_policy = str(body.get("session_policy") or "market-aware").strip().lower()
    if session_policy not in SESSION_POLICIES:
        raise ValueError("Unsupported alert session policy.")
    cooldown = int(body.get("cooldown_minutes") if body.get("cooldown_minutes") is not None else 60)
    if cooldown < 0 or cooldown > 10_080:
        raise ValueError("cooldown_minutes must be between 0 and 10080.")
    severity = str(body.get("severity") or "watch").strip().lower()
    if severity not in SEVERITIES:
        raise ValueError("Unsupported alert severity.")
    current = _utc(now)
    expires_at = str(body.get("expires_at") or "").strip() or None
    expiry = _parse_time(expires_at)
    if expires_at and not expiry:
        raise ValueError("Invalid alert expiration timestamp.")
    if expiry and expiry <= current:
        raise ValueError("Alert expiration must be in the future.")
    if expiry and expiry > current + timedelta(days=366):
        raise ValueError("Alert expiration exceeds the one-year bound.")

    threshold = body.get("threshold")
    threshold_unit = str(body.get("threshold_unit") or "").strip()[:24]
    if rule_type in {"price_above", "price_below"}:
        threshold = _finite_number(threshold, label="Price threshold")
        if threshold < 0:
            raise ValueError("Price threshold cannot be negative.")
        threshold_unit = threshold_unit or "price"
    elif rule_type == "absolute_percent_move":
        threshold = _finite_number(threshold, label="Percent threshold")
        if threshold <= 0 or threshold > 1_000:
            raise ValueError("Percent threshold must be greater than zero and at most 1000.")
        threshold_unit = "%"
    elif rule_type == "material_saved_change":
        threshold = str(threshold or "material").strip().lower()
        if threshold not in {"info", "material", "high", "critical"}:
            raise ValueError("Saved-change threshold must be info, material, high, or critical.")
        threshold_unit = "severity"
    else:
        threshold = str(threshold or "stale").strip().lower()
        if threshold not in {"cached", "aging", "stale", "rate-limited", "unavailable"}:
            raise ValueError("Source degradation threshold is unsupported.")
        threshold_unit = "status"
    expected_version = body.get("expected_version", 0)
    if not isinstance(expected_version, int) or expected_version < 0:
        raise ValueError("expected_version must be a non-negative integer.")
    return {
        "watchlist_id": watchlist_id,
        "symbol": symbol,
        "rule_type": rule_type,
        "metric": definition["metric"],
        "operator": definition["operator"],
        "threshold": threshold,
        "threshold_unit": threshold_unit,
        "frequency": frequency,
        "frequency_minutes": FREQUENCIES[frequency],
        "session_policy": session_policy,
        "cooldown_minutes": cooldown,
        "severity": severity,
        "expires_at": expiry.replace(microsecond=0).isoformat() if expiry else None,
        "expected_version": expected_version,
        "delivery": "in-app-only",
    }


def validate_evaluation_request(body: dict[str, Any] | None) -> dict[str, Any]:
    candidate = dict(body or {})
    if _CLIENT_IDENTITY_FIELDS.intersection(candidate):
        raise ValueError("Tenant and user identity are server-derived.")
    allowed = {"idempotency_key", "mode", "cancelled"}
    if set(candidate) - allowed:
        raise ValueError("Unsupported alert evaluation field.")
    key = str(candidate.get("idempotency_key") or "").strip()
    if not _SAFE_IDEMPOTENCY.fullmatch(key):
        raise ValueError("Invalid alert evaluation idempotency key.")
    mode = str(candidate.get("mode") or "manual").strip().lower()
    if mode not in {"manual", "worker"}:
        raise ValueError("Alert evaluation mode must be manual or worker.")
    return {"idempotency_key": key, "mode": mode, "cancelled": bool(candidate.get("cancelled"))}


class WatchlistAlertManagerStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path

    @staticmethod
    def _audit(
        conn: Any,
        tenant_id: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        event_type: str,
        prior_state: str,
        new_state: str,
        timestamp: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            "INSERT INTO tenant_watchlist_alert_audit (event_id, tenant_id, owner_user_id, resource_type, resource_id, event_type, prior_state, new_state, detail_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id("alaa"), tenant_id, user_id, resource_type, resource_id, event_type, prior_state, new_state, json_dumps(detail or {}), timestamp),
        )

    def _watchlist_item(self, tenant_id: str, watchlist_id: str, symbol: str) -> dict[str, Any] | None:
        return execute_query(
            """
            SELECT item.*, list.name AS watchlist_name
            FROM tenant_watchlist_items item
            JOIN tenant_watchlists list
              ON list.tenant_id=item.tenant_id AND list.resource_id=item.watchlist_resource_id
            WHERE item.tenant_id=? AND item.watchlist_resource_id=? AND item.symbol=?
              AND item.active=1 AND list.active=1
            """,
            (tenant_id, watchlist_id, symbol), fetch=True, one=True, db_path=self.db_path,
        )  # type: ignore[return-value]

    @staticmethod
    def _rule_from_row(row: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        threshold = json_loads(row.get("threshold_json"), row.get("threshold_json"))
        state = str(row.get("state") or "paused")
        expiry = _parse_time(row.get("expires_at"))
        if state == "active" and expiry and expiry <= _utc(now):
            state = "expired"
        return public_account_payload(
            {
                "resource_id": row.get("resource_id"),
                "watchlist_id": row.get("watchlist_resource_id"),
                "symbol": row.get("symbol"),
                "asset_class": row.get("asset_class"),
                "rule_type": row.get("rule_type"),
                "metric": row.get("metric"),
                "operator": row.get("operator"),
                "threshold": threshold,
                "threshold_unit": row.get("threshold_unit"),
                "severity": row.get("severity"),
                "state": state,
                "state_reason": {
                    "active": "scheduled",
                    "paused": "stopped-manually",
                    "expired": "stopped-expired",
                    "cancelled": "stopped-cancelled",
                    "deleted": "deleted-by-user",
                }.get(state, "unknown"),
                "schedule": {
                    "frequency": row.get("frequency"),
                    "frequency_minutes": int(row.get("frequency_minutes") or 0),
                    "session_policy": row.get("session_policy"),
                    "next_due_at": row.get("next_due_at"),
                    "calendar_status": "continuous" if row.get("session_policy") == "continuous" else "proxy-unverified",
                },
                "cooldown_minutes": int(row.get("cooldown_minutes") or 0),
                "expires_at": row.get("expires_at"),
                "last_evaluated_at": row.get("last_evaluated_at"),
                "last_triggered_at": row.get("last_triggered_at"),
                "next_due_at": row.get("next_due_at"),
                "last_snapshot_id": row.get("last_snapshot_id"),
                "version": int(row.get("version") or 1),
                "delivery": "in-app-only",
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
            }
        )

    @staticmethod
    def _evaluation_from_row(row: dict[str, Any], *, replay: bool = False) -> dict[str, Any]:
        output = {
            "run_id": row.get("run_id"),
            "status": row.get("status"),
            "mode": row.get("mode"),
            "due_count": int(row.get("due_count") or 0),
            "evaluated_count": int(row.get("evaluated_count") or 0),
            "triggered_count": int(row.get("triggered_count") or 0),
            "deduped_count": int(row.get("deduped_count") or 0),
            "data_gap_count": int(row.get("data_gap_count") or 0),
            "quota_blocked_count": int(row.get("quota_blocked_count") or 0),
            "provider_call_count": int(row.get("provider_call_count") or 0),
            "source_clock": json_loads(row.get("source_clock_json"), {}),
            "detail": json_loads(row.get("detail_json"), {}),
            "started_at": row.get("started_at"),
            "completed_at": row.get("completed_at"),
            "duration_ms": int(row.get("duration_ms") or 0),
            "idempotent_replay": replay,
        }
        return public_account_payload(output)

    @staticmethod
    def _evidence_links(row: dict[str, Any]) -> list[dict[str, str]]:
        symbol = str(row.get("symbol") or "")
        trigger_id = str(row.get("trigger_id") or "")
        origin_state = urlencode({"view": "alert-manager", "tab": "history", "selected": trigger_id})
        common = {"originView": "alert-manager", "originState": origin_state, "originId": trigger_id}
        analyst = urlencode({"view": "analyst-workspace", "symbol": symbol, "assetClass": "equity", "panel": "catalysts", **common})
        news = urlencode({"view": "news", "topic": symbol, **common})
        brief = urlencode({"view": "daily-brief", "period": "morning", "section": "markets", **common})
        risk_map = urlencode({"view": "war-room-map", "selected": "", **common})
        return [
            {"kind": "analyst", "label": "Analyst", "href": f"/?{analyst}"},
            {"kind": "news", "label": "News", "href": f"/?{news}"},
            {"kind": "brief", "label": "Brief", "href": f"/?{brief}"},
            {"kind": "map", "label": "Map", "href": f"/?{risk_map}"},
        ]

    @classmethod
    def _trigger_from_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        evidence = json_loads(row.get("evidence_json"), {})
        output = {
            "trigger_id": row.get("trigger_id"),
            "rule_id": row.get("rule_resource_id"),
            "watchlist_id": row.get("watchlist_resource_id"),
            "evaluation_run_id": row.get("evaluation_run_id"),
            "symbol": row.get("symbol"),
            "status": row.get("status"),
            "severity": row.get("severity"),
            "review_state": row.get("review_state"),
            "metric": row.get("metric"),
            "operator": row.get("operator"),
            "threshold": json_loads(row.get("threshold_json"), row.get("threshold_json")),
            "observed_value": json_loads(row.get("observed_value_json"), row.get("observed_value_json")),
            "source_status": row.get("source_status"),
            "provider": row.get("provider"),
            "source_url": row.get("source_url"),
            "message": row.get("message"),
            "caveat": row.get("caveat"),
            "data_gap": row.get("data_gap"),
            "evidence": evidence,
            "clocks": {
                "observed_at": row.get("observed_at"),
                "retrieved_at": row.get("retrieved_at"),
                "evaluated_at": row.get("evaluated_at"),
                "triggered_at": row.get("triggered_at"),
                "reviewed_at": row.get("reviewed_at"),
            },
            "version": int(row.get("version") or 1),
            "live_intelligence_claimed": _normalize_source_status(row.get("source_status")) in {"live/fresh", "fresh"},
            "not_financial_advice": True,
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }
        output["evidence_links"] = cls._evidence_links({**row, "trigger_id": output["trigger_id"]})
        return public_account_payload(output)

    def create_rule(self, context: dict[str, Any], body: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        validated = validate_alert_rule_request(body, now=now)
        item = self._watchlist_item(tenant_id, validated["watchlist_id"], validated["symbol"])
        if not item:
            raise KeyError("Saved Watchlist symbol not found.")
        timestamp = _iso(now)
        fingerprint = _stable_hash({key: validated[key] for key in ("watchlist_id", "symbol", "rule_type", "threshold", "threshold_unit", "frequency", "session_policy")})
        with get_connection(self.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM tenant_watchlist_alert_rules WHERE tenant_id=? AND state!='deleted'",
                (tenant_id,),
            ).fetchone()[0]
            if int(count) >= MAX_ALERT_RULES:
                raise ValueError("Tenant alert rule limit reached.")
            duplicate = conn.execute(
                "SELECT resource_id FROM tenant_watchlist_alert_rules WHERE tenant_id=? AND fingerprint=? AND state!='deleted' LIMIT 1",
                (tenant_id, fingerprint),
            ).fetchone()
            if duplicate:
                raise ValueError("An equivalent active alert rule already exists.")
            rule_id = new_id("wlar")
            conn.execute(
                """
                INSERT INTO tenant_watchlist_alert_rules (
                    resource_id, tenant_id, owner_user_id, watchlist_resource_id, symbol, asset_class,
                    rule_type, metric, operator, threshold_json, threshold_unit, frequency,
                    frequency_minutes, session_policy, cooldown_minutes, severity, state, fingerprint,
                    next_due_at, expires_at, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, 1, ?, ?)
                """,
                (
                    rule_id, tenant_id, user_id, validated["watchlist_id"], validated["symbol"], item.get("asset_class") or "",
                    validated["rule_type"], validated["metric"], validated["operator"], json_dumps(validated["threshold"]),
                    validated["threshold_unit"], validated["frequency"], validated["frequency_minutes"],
                    validated["session_policy"], validated["cooldown_minutes"], validated["severity"], fingerprint,
                    timestamp, validated["expires_at"], timestamp, timestamp,
                ),
            )
            self._audit(conn, tenant_id, user_id, "rule", rule_id, "rule-created", "", "active", timestamp, {"rule_type": validated["rule_type"], "symbol": validated["symbol"]})
            row = conn.execute("SELECT * FROM tenant_watchlist_alert_rules WHERE resource_id=?", (rule_id,)).fetchone()
        return self._rule_from_row(dict(row), now=now)

    def get_rule(self, context: dict[str, Any], resource_id: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        if not _SAFE_ID.fullmatch(str(resource_id or "")):
            return None
        row = execute_query(
            "SELECT * FROM tenant_watchlist_alert_rules WHERE tenant_id=? AND resource_id=?",
            (tenant_id, resource_id), fetch=True, one=True, db_path=self.db_path,
        )
        return self._rule_from_row(row) if isinstance(row, dict) else None

    def list_rules(self, context: dict[str, Any], *, include_deleted: bool = True, limit: int = MAX_ALERT_RULES) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        bounded = max(1, min(int(limit), MAX_ALERT_RULES))
        where = "" if include_deleted else "AND state!='deleted'"
        rows = execute_query(
            f"SELECT * FROM tenant_watchlist_alert_rules WHERE tenant_id=? {where} ORDER BY updated_at DESC, resource_id LIMIT ?",
            (tenant_id, bounded), fetch=True, db_path=self.db_path,
        )
        return [self._rule_from_row(row) for row in rows or []]  # type: ignore[arg-type]

    def update_rule(self, context: dict[str, Any], resource_id: str, body: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        if not isinstance(body, dict) or _CLIENT_IDENTITY_FIELDS.intersection(body):
            raise ValueError("Invalid alert rule update.")
        action = str(body.get("action") or "").strip().lower()
        if action not in {"pause", "resume", "cancel"}:
            raise ValueError("Unsupported alert lifecycle action.")
        expected_version = body.get("expected_version")
        if not isinstance(expected_version, int) or expected_version < 1:
            raise ValueError("expected_version must be a positive integer.")
        target = {"pause": "paused", "resume": "active", "cancel": "cancelled"}[action]
        timestamp = _iso(now)
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tenant_watchlist_alert_rules WHERE tenant_id=? AND resource_id=?",
                (tenant_id, resource_id),
            ).fetchone()
            if not row:
                raise KeyError("Alert rule not found.")
            existing = dict(row)
            current_version = int(existing.get("version") or 1)
            if current_version != expected_version:
                raise AlertManagerConflict(current_version)
            prior = str(existing.get("state") or "paused")
            if prior == "deleted":
                raise ValueError("Deleted alert rules cannot be changed.")
            if action == "resume" and _parse_time(existing.get("expires_at")) and _parse_time(existing.get("expires_at")) <= _utc(now):
                target = "expired"
            next_due = timestamp if target == "active" else existing.get("next_due_at")
            conn.execute(
                "UPDATE tenant_watchlist_alert_rules SET state=?, next_due_at=?, version=version+1, updated_at=? WHERE tenant_id=? AND resource_id=?",
                (target, next_due, timestamp, tenant_id, resource_id),
            )
            self._audit(conn, tenant_id, user_id, "rule", resource_id, f"rule-{action}d" if action != "pause" else "rule-paused", prior, target, timestamp)
            updated = conn.execute("SELECT * FROM tenant_watchlist_alert_rules WHERE tenant_id=? AND resource_id=?", (tenant_id, resource_id)).fetchone()
        return self._rule_from_row(dict(updated), now=now)

    def delete_rule(self, context: dict[str, Any], resource_id: str, *, expected_version: int, now: datetime | None = None) -> bool:
        tenant_id, user_id = _require_authenticated(context)
        timestamp = _iso(now)
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT state, version FROM tenant_watchlist_alert_rules WHERE tenant_id=? AND resource_id=?",
                (tenant_id, resource_id),
            ).fetchone()
            if not row:
                return False
            if int(row["version"]) != int(expected_version):
                raise AlertManagerConflict(int(row["version"]))
            prior = str(row["state"])
            conn.execute(
                "UPDATE tenant_watchlist_alert_rules SET state='deleted', deleted_at=?, version=version+1, updated_at=? WHERE tenant_id=? AND resource_id=?",
                (timestamp, timestamp, tenant_id, resource_id),
            )
            self._audit(conn, tenant_id, user_id, "rule", resource_id, "rule-deleted", prior, "deleted", timestamp)
        return True

    def _expire_rules(self, conn: Any, tenant_id: str, user_id: str, current: datetime) -> None:
        timestamp = _iso(current)
        rows = conn.execute(
            "SELECT resource_id FROM tenant_watchlist_alert_rules WHERE tenant_id=? AND state='active' AND expires_at IS NOT NULL AND expires_at<=?",
            (tenant_id, timestamp),
        ).fetchall()
        for row in rows:
            conn.execute(
                "UPDATE tenant_watchlist_alert_rules SET state='expired', version=version+1, updated_at=? WHERE tenant_id=? AND resource_id=?",
                (timestamp, tenant_id, row["resource_id"]),
            )
            self._audit(conn, tenant_id, user_id, "rule", row["resource_id"], "rule-expired", "active", "expired", timestamp)

    def plan_due(self, context: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        current = _utc(now)
        timestamp = _iso(current)
        with get_connection(self.db_path) as conn:
            self._expire_rules(conn, tenant_id, user_id, current)
            rows = conn.execute(
                "SELECT * FROM tenant_watchlist_alert_rules WHERE tenant_id=? AND state!='deleted' ORDER BY next_due_at, resource_id LIMIT ?",
                (tenant_id, MAX_ALERT_RULES),
            ).fetchall()
        rules = [self._rule_from_row(dict(row), now=current) for row in rows]
        due = [row for row in rules if row["state"] == "active" and str(row["schedule"].get("next_due_at") or "") <= timestamp]
        return {
            "planned_at": timestamp,
            "due": due,
            "not_due": [row for row in rules if row not in due],
            "due_count": len(due),
            "bounded_count": len(rules),
            "maximum_rules": MAX_ALERT_RULES,
            "provider_call_count": 0,
        }

    @staticmethod
    def _latest_snapshot(conn: Any, tenant_id: str, rule: dict[str, Any]) -> dict[str, Any] | None:
        row = conn.execute(
            """
            SELECT snapshot.*, run.diff_json AS run_diff_json, run.status AS run_status
            FROM tenant_observation_snapshots snapshot
            JOIN tenant_observation_runs run
              ON run.tenant_id=snapshot.tenant_id AND run.run_id=snapshot.run_id
            WHERE snapshot.tenant_id=? AND snapshot.watchlist_resource_id=? AND snapshot.symbol=?
              AND run.status IN ('completed','partial')
            ORDER BY snapshot.created_at DESC, snapshot.snapshot_id DESC LIMIT 1
            """,
            (tenant_id, rule["watchlist_resource_id"], rule["symbol"]),
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _latest_observation_gap(conn: Any, tenant_id: str, rule: dict[str, Any]) -> dict[str, str]:
        rows = conn.execute(
            """
            SELECT status, requested_symbols_json, missing_capabilities_json,
                   provider_states_json, error_code
            FROM tenant_observation_runs
            WHERE tenant_id=? AND watchlist_resource_id=?
            ORDER BY created_at DESC, run_id DESC LIMIT 10
            """,
            (tenant_id, rule["watchlist_resource_id"]),
        ).fetchall()
        symbol = str(rule.get("symbol") or "").upper()
        for raw in rows:
            row = dict(raw)
            requested = [str(value).upper() for value in json_loads(row.get("requested_symbols_json"), []) if value]
            if requested and symbol not in requested:
                continue
            missing = json_loads(row.get("missing_capabilities_json"), [])
            states = json_loads(row.get("provider_states_json"), [])
            evidence = json.dumps(
                {"status": row.get("status"), "missing": missing, "states": states, "error": row.get("error_code")},
                ensure_ascii=True,
                sort_keys=True,
                default=str,
            ).lower()
            if "quota" in evidence or "budget-exhausted" in evidence:
                return {"status": "quota-blocked", "reason": "latest-observation-quota-blocked"}
            if missing or states or str(row.get("status") or "") in {"failed", "partial", "cancelled"}:
                return {"status": "provider-unavailable", "reason": "latest-observation-did-not-produce-a-validated-snapshot"}
        return {"status": "provider-unavailable", "reason": "no-validated-observation"}

    @staticmethod
    def _resolve_metric(rule: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        payload = json_loads(snapshot.get("payload_json"), {})
        quote = payload.get("quote") if isinstance(payload.get("quote"), dict) else {}
        source_status = _normalize_source_status(snapshot.get("source_status") or quote.get("source_status"))
        rule_type = str(rule.get("rule_type"))
        threshold = json_loads(rule.get("threshold_json"), rule.get("threshold_json"))
        if rule_type != "source_degradation" and source_status in BLOCKED_MARKET_STATUSES:
            return {
                "status": "skipped_data_gap", "triggered": False, "observed": None,
                "message": "Stored evidence is stale or unavailable; no market-condition trigger was created.",
                "data_gap": f"Source status {source_status} is not eligible for a market-condition trigger.",
            }
        if rule_type in {"price_above", "price_below"}:
            observed = quote.get("last_price")
            comparable = observed
            legacy_operator = "above" if rule_type == "price_above" else "below"
            legacy_threshold = threshold
        elif rule_type == "absolute_percent_move":
            raw = quote.get("change_pct")
            observed = abs(float(raw)) if raw is not None else None
            comparable = observed
            legacy_operator = "above"
            legacy_threshold = threshold
        elif rule_type == "material_saved_change":
            diff = json_loads(snapshot.get("run_diff_json"), {})
            summary = diff.get("summary") if isinstance(diff.get("summary"), dict) else {}
            changes = diff.get("changes") if isinstance(diff.get("changes"), list) else []
            symbol_changes = [row for row in changes if str((row or {}).get("symbol") or "").upper() == str(rule.get("symbol") or "").upper()]
            observed_label = "material" if symbol_changes or int(diff.get("material_change_count") or summary.get("material_change_count") or 0) > 0 else "info"
            rank = {"info": 0, "material": 1, "high": 2, "critical": 3}
            observed = observed_label
            comparable = rank[observed_label]
            legacy_operator = "above"
            legacy_threshold = rank.get(str(threshold), 1) - 0.5
        else:
            observed = source_status
            comparable = DEGRADED_STATUS_RANK.get(source_status, 4)
            legacy_operator = "above"
            legacy_threshold = DEGRADED_STATUS_RANK.get(str(threshold), 2) - 0.5
        if comparable is None:
            return {
                "status": "skipped_data_gap", "triggered": False, "observed": None,
                "message": f"Stored observation does not contain {rule.get('metric')}.",
                "data_gap": f"Metric {rule.get('metric')} is unavailable in the latest validated snapshot.",
            }
        legacy_rule = {
            "alert_id": rule.get("resource_id"),
            "metric": "phase6o_observed",
            "operator": legacy_operator,
            "threshold": legacy_threshold,
            "severity": rule.get("severity") or "watch",
            "cooldown_minutes": int(rule.get("cooldown_minutes") or 0),
            "last_triggered_at": rule.get("last_triggered_at"),
        }
        result = evaluate_alert_rule(
            legacy_rule,
            {
                "phase6o_observed": comparable,
                "source_snapshot": {
                    "provider": snapshot.get("provider"),
                    "source_url": snapshot.get("source_url"),
                    "source_status": source_status,
                    "freshness": snapshot.get("snapshot_status"),
                    "confidence": snapshot.get("confidence"),
                },
                "data_confidence": snapshot.get("confidence"),
            },
            persist=False,
        )
        result["observed"] = observed
        result["data_gap"] = ""
        return result

    def evaluate_due(self, context: dict[str, Any], body: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        request = validate_evaluation_request(body)
        current = _utc(now)
        timestamp = _iso(current)
        started = time.perf_counter()
        with get_connection(self.db_path) as conn:
            replay = conn.execute(
                "SELECT * FROM tenant_watchlist_alert_evaluations WHERE tenant_id=? AND idempotency_key=?",
                (tenant_id, request["idempotency_key"]),
            ).fetchone()
            if replay:
                return self._evaluation_from_row(dict(replay), replay=True)
            self._expire_rules(conn, tenant_id, user_id, current)
            rules = [dict(row) for row in conn.execute(
                "SELECT * FROM tenant_watchlist_alert_rules WHERE tenant_id=? AND state='active' AND (next_due_at IS NULL OR next_due_at<=?) ORDER BY next_due_at, resource_id LIMIT ?",
                (tenant_id, timestamp, MAX_ALERT_RULES),
            ).fetchall()]
            run_id = new_id("alertrun")
            request_fingerprint = _stable_hash({"tenant": tenant_id, "key": request["idempotency_key"], "mode": request["mode"]})
            due_count = len(rules)
            evaluated = triggered = deduped = gaps = quota_blocked = 0
            clocks: list[dict[str, Any]] = []
            detail_rows: list[dict[str, Any]] = []
            if request["cancelled"]:
                status = "cancelled"
                rules = []
            else:
                status = "completed" if rules else "no-due"
            for rule in rules:
                evaluated += 1
                snapshot = self._latest_snapshot(conn, tenant_id, rule)
                next_due = _iso(current + timedelta(minutes=int(rule.get("frequency_minutes") or 15)))
                if not snapshot:
                    gap = self._latest_observation_gap(conn, tenant_id, rule)
                    if gap["status"] == "quota-blocked":
                        quota_blocked += 1
                    else:
                        gaps += 1
                    detail_rows.append({"rule_id": rule["resource_id"], "status": gap["status"], "reason": gap["reason"]})
                    conn.execute(
                        "UPDATE tenant_watchlist_alert_rules SET last_evaluated_at=?, next_due_at=?, updated_at=? WHERE tenant_id=? AND resource_id=?",
                        (timestamp, next_due, timestamp, tenant_id, rule["resource_id"]),
                    )
                    continue
                result = self._resolve_metric(rule, snapshot)
                trigger_created = False
                clocks.append({"observed_at": snapshot.get("observed_at"), "retrieved_at": snapshot.get("retrieved_at")})
                if result.get("status") == "skipped_data_gap":
                    gaps += 1
                elif result.get("status") == "skipped_cooldown":
                    deduped += 1
                if result.get("triggered"):
                    dedupe_key = _stable_hash({
                        "rule_id": rule["resource_id"],
                        "snapshot_id": snapshot["snapshot_id"],
                        "content_hash": snapshot.get("content_hash"),
                        "observed": result.get("observed"),
                    })
                    existing = conn.execute(
                        "SELECT trigger_id FROM tenant_watchlist_alert_triggers WHERE tenant_id=? AND dedupe_key=?",
                        (tenant_id, dedupe_key),
                    ).fetchone()
                    if existing:
                        deduped += 1
                        result["status"] = "deduped_existing"
                    else:
                        trigger_id = new_id("altrg")
                        source_status = _normalize_source_status(snapshot.get("source_status"))
                        message = f"{rule['symbol']} {str(rule['rule_type']).replace('_', ' ')} matched the stored observation."
                        evidence = {
                            "snapshot_id": snapshot["snapshot_id"],
                            "observation_run_id": snapshot["run_id"],
                            "content_hash": snapshot.get("content_hash"),
                            "snapshot_status": snapshot.get("snapshot_status"),
                            "source_status": source_status,
                            "confidence": snapshot.get("confidence"),
                        }
                        conn.execute(
                            """
                            INSERT INTO tenant_watchlist_alert_triggers (
                                trigger_id, tenant_id, owner_user_id, rule_resource_id, watchlist_resource_id,
                                evaluation_run_id, snapshot_id, symbol, dedupe_key, status, severity, review_state,
                                metric, operator, threshold_json, observed_value_json, source_status, provider,
                                source_url, observed_at, retrieved_at, evaluated_at, triggered_at, message,
                                caveat, data_gap, evidence_json, version, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'triggered', ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                            """,
                            (
                                trigger_id, tenant_id, user_id, rule["resource_id"], rule["watchlist_resource_id"],
                                run_id, snapshot["snapshot_id"], rule["symbol"], dedupe_key, rule.get("severity") or "watch",
                                rule["metric"], rule["operator"], rule["threshold_json"], json_dumps(_json_scalar(result.get("observed"))),
                                source_status, snapshot.get("provider") or "", snapshot.get("source_url") or "",
                                snapshot.get("observed_at"), snapshot.get("retrieved_at"), timestamp, timestamp, message,
                                snapshot.get("caveat") or "", snapshot.get("data_gap") or "", json_dumps(evidence), timestamp, timestamp,
                            ),
                        )
                        self._audit(conn, tenant_id, user_id, "trigger", trigger_id, "trigger-created", "", "new", timestamp, {"rule_id": rule["resource_id"], "snapshot_id": snapshot["snapshot_id"]})
                        triggered += 1
                        trigger_created = True
                conn.execute(
                    "UPDATE tenant_watchlist_alert_rules SET last_evaluated_at=?, last_triggered_at=CASE WHEN ? THEN ? ELSE last_triggered_at END, next_due_at=?, last_snapshot_id=?, last_observed_value_json=?, updated_at=? WHERE tenant_id=? AND resource_id=?",
                    (
                        timestamp, 1 if trigger_created else 0,
                        timestamp, next_due, snapshot["snapshot_id"], json_dumps(_json_scalar(result.get("observed"))),
                        timestamp, tenant_id, rule["resource_id"],
                    ),
                )
                detail_rows.append({"rule_id": rule["resource_id"], "status": result.get("status"), "matched": bool(result.get("triggered")), "triggered": trigger_created, "snapshot_id": snapshot["snapshot_id"]})
            if quota_blocked and evaluated and quota_blocked == evaluated:
                status = "quota-blocked"
            elif (gaps or quota_blocked) and evaluated:
                status = "partial"
            source_clock = {
                "observed_at": max((str(row.get("observed_at")) for row in clocks if row.get("observed_at")), default=None),
                "retrieved_at": max((str(row.get("retrieved_at")) for row in clocks if row.get("retrieved_at")), default=None),
                "evaluated_at": timestamp,
            }
            duration_ms = max(0, int((time.perf_counter() - started) * 1000))
            conn.execute(
                """
                INSERT INTO tenant_watchlist_alert_evaluations (
                    run_id, tenant_id, owner_user_id, idempotency_key, request_fingerprint, mode, status,
                    due_count, evaluated_count, triggered_count, deduped_count, data_gap_count,
                    quota_blocked_count, provider_call_count, source_clock_json, detail_json,
                    started_at, completed_at, duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, tenant_id, user_id, request["idempotency_key"], request_fingerprint, request["mode"], status,
                    due_count, evaluated, triggered, deduped, gaps, quota_blocked, json_dumps(source_clock),
                    json_dumps({"evaluations": detail_rows[:MAX_ALERT_RULES], "market_provider_calls": 0}),
                    timestamp, timestamp, duration_ms, timestamp,
                ),
            )
            self._audit(conn, tenant_id, user_id, "evaluation", run_id, "evaluation-completed", "queued", status, timestamp, {"due_count": due_count, "triggered_count": triggered, "provider_call_count": 0})
            row = conn.execute("SELECT * FROM tenant_watchlist_alert_evaluations WHERE run_id=?", (run_id,)).fetchone()
        return self._evaluation_from_row(dict(row))

    def list_evaluations(self, context: dict[str, Any], *, limit: int = 20) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        bounded = max(1, min(int(limit), MAX_ALERT_RUNS))
        rows = execute_query(
            "SELECT * FROM tenant_watchlist_alert_evaluations WHERE tenant_id=? ORDER BY created_at DESC, run_id DESC LIMIT ?",
            (tenant_id, bounded), fetch=True, db_path=self.db_path,
        )
        return [self._evaluation_from_row(row) for row in rows or []]  # type: ignore[arg-type]

    def list_triggers(self, context: dict[str, Any], *, limit: int = 100) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        bounded = max(1, min(int(limit), MAX_ALERT_TRIGGERS))
        rows = execute_query(
            "SELECT * FROM tenant_watchlist_alert_triggers WHERE tenant_id=? ORDER BY triggered_at DESC, trigger_id DESC LIMIT ?",
            (tenant_id, bounded), fetch=True, db_path=self.db_path,
        )
        return [self._trigger_from_row(row) for row in rows or []]  # type: ignore[arg-type]

    def get_trigger(self, context: dict[str, Any], trigger_id: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        row = execute_query(
            "SELECT * FROM tenant_watchlist_alert_triggers WHERE tenant_id=? AND trigger_id=?",
            (tenant_id, trigger_id), fetch=True, one=True, db_path=self.db_path,
        )
        return self._trigger_from_row(row) if isinstance(row, dict) else None

    def review_trigger(self, context: dict[str, Any], trigger_id: str, body: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        if not isinstance(body, dict) or _CLIENT_IDENTITY_FIELDS.intersection(body):
            raise ValueError("Invalid trigger review request.")
        action = str(body.get("action") or "").strip().lower()
        if action not in {"review", "acknowledge"}:
            raise ValueError("Trigger action must be review or acknowledge.")
        expected = body.get("expected_version")
        if not isinstance(expected, int) or expected < 1:
            raise ValueError("expected_version must be a positive integer.")
        timestamp = _iso(now)
        target = "reviewed" if action == "review" else "acknowledged"
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tenant_watchlist_alert_triggers WHERE tenant_id=? AND trigger_id=?",
                (tenant_id, trigger_id),
            ).fetchone()
            if not row:
                raise KeyError("Alert trigger not found.")
            existing = dict(row)
            if int(existing.get("version") or 1) != expected:
                raise AlertManagerConflict(int(existing.get("version") or 1))
            prior = str(existing.get("review_state") or "new")
            reviewed_at = existing.get("reviewed_at") or timestamp
            acknowledged_at = timestamp if action == "acknowledge" else existing.get("acknowledged_at")
            conn.execute(
                "UPDATE tenant_watchlist_alert_triggers SET review_state=?, reviewed_at=?, acknowledged_at=?, version=version+1, updated_at=? WHERE tenant_id=? AND trigger_id=?",
                (target, reviewed_at, acknowledged_at, timestamp, tenant_id, trigger_id),
            )
            self._audit(conn, tenant_id, user_id, "trigger", trigger_id, f"trigger-{target}", prior, target, timestamp)
            updated = conn.execute("SELECT * FROM tenant_watchlist_alert_triggers WHERE tenant_id=? AND trigger_id=?", (tenant_id, trigger_id)).fetchone()
        return self._trigger_from_row(dict(updated))

    def list_audit(self, context: dict[str, Any], *, limit: int = 100) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        bounded = max(1, min(int(limit), MAX_ALERT_AUDIT_ROWS))
        rows = execute_query(
            "SELECT resource_type, resource_id, event_type, prior_state, new_state, detail_json, created_at FROM tenant_watchlist_alert_audit WHERE tenant_id=? ORDER BY created_at DESC, event_id DESC LIMIT ?",
            (tenant_id, bounded), fetch=True, db_path=self.db_path,
        )
        return [public_account_payload({**row, "detail": json_loads(row.get("detail_json"), {})}) for row in rows or []]  # type: ignore[arg-type]

    def list_watchlists(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        rows = execute_query(
            """
            SELECT list.resource_id AS watchlist_id, list.name, item.symbol, item.display_name,
                   item.asset_class, item.exchange, item.source_status
            FROM tenant_watchlists list
            JOIN tenant_watchlist_items item
              ON item.tenant_id=list.tenant_id AND item.watchlist_resource_id=list.resource_id
            WHERE list.tenant_id=? AND list.active=1 AND item.active=1
            ORDER BY list.updated_at DESC, item.position, item.symbol LIMIT 100
            """,
            (tenant_id,), fetch=True, db_path=self.db_path,
        )
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows or []:  # type: ignore[assignment]
            watchlist_id = str(row.get("watchlist_id"))
            target = grouped.setdefault(watchlist_id, {"watchlist_id": watchlist_id, "name": row.get("name"), "items": []})
            target["items"].append({key: row.get(key) for key in ("symbol", "display_name", "asset_class", "exchange", "source_status")})
        return list(grouped.values())

    def get_worker_state(self, context: dict[str, Any]) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        row = execute_query(
            "SELECT * FROM tenant_watchlist_alert_worker_state WHERE tenant_id=?",
            (tenant_id,), fetch=True, one=True, db_path=self.db_path,
        )
        if not isinstance(row, dict):
            return None
        return public_account_payload(
            {
                "state": row.get("state"), "enabled": bool(row.get("enabled")),
                "last_started_at": row.get("last_started_at"), "last_heartbeat_at": row.get("last_heartbeat_at"),
                "last_stopped_at": row.get("last_stopped_at"), "last_evaluation_run_id": row.get("last_evaluation_run_id"),
                "restart_count": int(row.get("restart_count") or 0), "error_code": row.get("error_code"),
                "version": int(row.get("version") or 1), "updated_at": row.get("updated_at"),
            }
        )

    def mark_worker_state(
        self,
        context: dict[str, Any],
        state: str,
        *,
        run_id: str | None = None,
        error_code: str = "",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        normalized = str(state or "").lower()
        if normalized not in {"starting", "idle", "running", "stopped", "offline", "restarted"}:
            raise ValueError("Unsupported alert worker state.")
        timestamp = _iso(now)
        enabled = _truthy(os.getenv("GLOBAL_TERMINAL_ALERT_WORKER_ENABLED"))
        with get_connection(self.db_path) as conn:
            existing = conn.execute("SELECT * FROM tenant_watchlist_alert_worker_state WHERE tenant_id=?", (tenant_id,)).fetchone()
            if existing:
                prior = str(existing["state"])
                restart_increment = 1 if normalized in {"starting", "restarted"} and prior in {"stopped", "offline"} else 0
                conn.execute(
                    """
                    UPDATE tenant_watchlist_alert_worker_state
                    SET owner_user_id=?, state=?, enabled=?,
                        last_started_at=CASE WHEN ? IN ('starting','restarted') THEN ? ELSE last_started_at END,
                        last_heartbeat_at=?, last_stopped_at=CASE WHEN ?='stopped' THEN ? ELSE last_stopped_at END,
                        last_evaluation_run_id=COALESCE(?, last_evaluation_run_id), restart_count=restart_count+?,
                        error_code=?, version=version+1, updated_at=? WHERE tenant_id=?
                    """,
                    (user_id, normalized, 1 if enabled else 0, normalized, timestamp, timestamp, normalized, timestamp, run_id, restart_increment, error_code[:80], timestamp, tenant_id),
                )
            else:
                prior = ""
                conn.execute(
                    "INSERT INTO tenant_watchlist_alert_worker_state (resource_id, tenant_id, owner_user_id, state, enabled, last_started_at, last_heartbeat_at, last_stopped_at, last_evaluation_run_id, restart_count, error_code, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 1, ?, ?)",
                    (new_id("alwk"), tenant_id, user_id, normalized, 1 if enabled else 0, timestamp if normalized in {"starting", "restarted"} else None, timestamp, timestamp if normalized == "stopped" else None, run_id, error_code[:80], timestamp, timestamp),
                )
            self._audit(conn, tenant_id, user_id, "worker", "tenant-worker", "worker-state", prior, normalized, timestamp, {"run_id": run_id})
        return self.get_worker_state(context) or {}

    def export_manager(self, context: dict[str, Any]) -> dict[str, Any]:
        _require_authenticated(context)
        return public_account_payload(
            {
                "contract_version": CONTRACT_VERSION,
                "exported_at": _iso(),
                "rules": self.list_rules(context),
                "triggers": self.list_triggers(context, limit=MAX_ALERT_TRIGGERS),
                "evaluations": self.list_evaluations(context, limit=MAX_ALERT_RUNS),
                "audit": self.list_audit(context, limit=MAX_ALERT_AUDIT_ROWS),
                "provider_call_count": 0,
                "delivery": "in-app-only",
                "private_notes_included": False,
            }
        )


def build_alert_worker_status(
    store: WatchlistAlertManagerStore,
    context: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    enabled = _truthy(os.getenv("GLOBAL_TERMINAL_ALERT_WORKER_ENABLED"))
    observe_requested = _truthy(os.getenv("GLOBAL_TERMINAL_ALERT_WORKER_OBSERVE_ENABLED"))
    saved = store.get_worker_state(context)
    current = _utc(now)
    heartbeat = _parse_time((saved or {}).get("last_heartbeat_at"))
    if not enabled:
        state = "stopped"
        reason = "explicit-opt-in-required"
    elif not saved or not heartbeat or heartbeat < current - timedelta(minutes=10):
        state = "offline"
        reason = "worker-heartbeat-missing"
    else:
        state = str(saved.get("state") or "offline")
        reason = "worker-heartbeat-observed"
    return public_account_payload(
        {
            "enabled": enabled,
            "state": state,
            "reason": reason,
            "view_starts_worker": False,
            "observation_jobs_enabled": False,
            "observation_jobs_requested": observe_requested,
            "observation_job_status": "unavailable-no-coordinator" if observe_requested else "disabled",
            "evaluation_source": "stored-phase6n-observations",
            "last_heartbeat_at": (saved or {}).get("last_heartbeat_at"),
            "last_evaluation_run_id": (saved or {}).get("last_evaluation_run_id"),
            "restart_count": int((saved or {}).get("restart_count") or 0),
            "manual_run_available": True,
            "provider_call_count": 0,
            "caveat": "The explicitly enabled local worker evaluates stored observations only; page views never start polling." if enabled else "The local worker is disabled until explicit opt-in. Page views never start polling.",
        }
    )


def run_alert_worker_once(
    context: dict[str, Any],
    *,
    store: WatchlistAlertManagerStore,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not _truthy(os.getenv("GLOBAL_TERMINAL_ALERT_WORKER_ENABLED")):
        return {"status": "disabled", "reason": "explicit-opt-in-required", "provider_call_count": 0}
    current = _utc(now)
    saved = store.get_worker_state(context)
    if saved and str(saved.get("state") or "") in {"stopped", "offline"}:
        store.mark_worker_state(context, "restarted", now=current)
    else:
        store.mark_worker_state(context, "starting", now=current)
    store.mark_worker_state(context, "running", now=current)
    bucket = int(current.timestamp()) // 300
    try:
        result = store.evaluate_due(
            context,
            {"idempotency_key": f"alert-worker-{bucket}", "mode": "worker"},
            now=current,
        )
        store.mark_worker_state(context, "idle", run_id=str(result.get("run_id") or ""), now=current)
        return result
    except Exception:
        store.mark_worker_state(context, "offline", error_code="worker-evaluation-failed", now=current)
        raise


def build_watchlist_alert_manager_contract(
    context: dict[str, Any],
    *,
    store: WatchlistAlertManagerStore | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    manager = store or WatchlistAlertManagerStore(os.getenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH") or None)
    rules = manager.list_rules(context)
    triggers = manager.list_triggers(context, limit=100)
    evaluations = manager.list_evaluations(context, limit=20)
    plan = manager.plan_due(context, now=now)
    active = [row for row in rules if row.get("state") == "active"]
    new_triggers = [row for row in triggers if row.get("review_state") == "new"]
    return public_account_payload(
        {
            "contract_version": CONTRACT_VERSION,
            "generated_at": _iso(now),
            "summary": {
                "status": "no-rules" if not rules else "ready",
                "rule_count": len(rules),
                "active_count": len(active),
                "due_count": int(plan.get("due_count") or 0),
                "trigger_count": len(triggers),
                "new_trigger_count": len(new_triggers),
                "provider_call_count": 0,
            },
            "watchlists": manager.list_watchlists(context),
            "rules": rules,
            "due_plan": plan,
            "triggers": triggers,
            "evaluations": evaluations,
            "worker": build_alert_worker_status(manager, context, now=now),
            "clock_legend": {
                "observation": "Market or source fact timestamp from the saved snapshot.",
                "retrieval": "Time the provider response was retrieved.",
                "evaluation": "Time the deterministic rule read the stored snapshot.",
                "trigger": "Time a deduplicated in-app trigger was persisted.",
                "review": "Time the user reviewed or acknowledged the trigger.",
            },
            "delivery_channels": {
                "in_app": "available",
                "email": "unavailable",
                "sms": "unavailable",
                "push": "unavailable",
                "webhook": "unavailable",
            },
            "bounds": {
                "maximum_rules": MAX_ALERT_RULES,
                "maximum_trigger_history": MAX_ALERT_TRIGGERS,
                "maximum_observation_symbols": 5,
                "maximum_observation_provider_calls": 16,
                "maximum_provider_concurrency": 2,
            },
            "hosted_readiness": {
                "status": "unavailable",
                "migration": "phase6o-required",
                "rls_ab_conformance": "not-run",
                "recovery_conformance": "not-run",
                "hosted_scheduler": "unavailable",
                "caveat": "Local account persistence is available. Hosted Phase 6O monitoring is not claimed.",
            },
            "legacy_preview": {
                "status": "deprecated-compatibility",
                "routes_retained": True,
                "replacement": "/api/account/alert-manager",
            },
            "state_catalog": ["no-rules", "active-due", "active-not-due", "triggered", "cooldown-deduped", "paused", "expired", "cancelled", "deleted", "quota-blocked", "partial-lkg", "provider-unavailable", "worker-stopped", "worker-offline", "worker-restarted", "conflict", "hosted-unavailable"],
            "research_only": True,
            "not_financial_advice": True,
        }
    )


def build_watchlist_alert_manager_fixture_contract() -> dict[str, Any]:
    observed = "2026-07-15T14:00:00+00:00"
    trigger = {
        "trigger_id": "fixture-alert-trigger-aapl",
        "rule_id": "fixture-alert-rule-aapl",
        "watchlist_id": "fixture-daily",
        "evaluation_run_id": "fixture-alert-run",
        "symbol": "AAPL",
        "status": "triggered",
        "severity": "high",
        "review_state": "new",
        "metric": "last_price",
        "operator": "above",
        "threshold": 200,
        "observed_value": 212.5,
        "source_status": "fixture",
        "provider": "phase6o.fixture",
        "source_url": "https://example.test/phase6o/aapl",
        "message": "AAPL price above matched the stored fictional observation.",
        "caveat": "Fictional fixture for deterministic product review.",
        "data_gap": "Not live market data.",
        "evidence": {"snapshot_id": "fixture-snapshot-aapl", "snapshot_status": "fixture", "confidence": 0.8},
        "clocks": {"observed_at": observed, "retrieved_at": observed, "evaluated_at": observed, "triggered_at": observed, "reviewed_at": None},
        "version": 1,
        "live_intelligence_claimed": False,
        "not_financial_advice": True,
    }
    trigger["evidence_links"] = WatchlistAlertManagerStore._evidence_links(trigger)
    return {
        "contract_version": CONTRACT_VERSION,
        "generated_at": observed,
        "summary": {"status": "ready", "rule_count": 2, "active_count": 1, "due_count": 0, "trigger_count": 1, "new_trigger_count": 1, "provider_call_count": 0},
        "watchlists": [{"watchlist_id": "fixture-daily", "name": "Daily Radar", "items": [{"symbol": "AAPL", "display_name": "Apple Inc.", "asset_class": "equity", "exchange": "NASDAQ", "source_status": "fixture"}, {"symbol": "BTCUSDT", "display_name": "Bitcoin", "asset_class": "crypto", "exchange": "Binance", "source_status": "fixture"}]}],
        "rules": [
            {"resource_id": "fixture-alert-rule-aapl", "watchlist_id": "fixture-daily", "symbol": "AAPL", "asset_class": "equity", "rule_type": "price_above", "metric": "last_price", "operator": "above", "threshold": 200, "threshold_unit": "USD", "severity": "high", "state": "active", "state_reason": "scheduled", "schedule": {"frequency": "15m", "frequency_minutes": 15, "session_policy": "market-aware", "next_due_at": "2026-07-15T14:15:00+00:00", "calendar_status": "proxy-unverified"}, "cooldown_minutes": 60, "expires_at": "2026-07-22T14:00:00+00:00", "last_evaluated_at": observed, "last_triggered_at": observed, "last_snapshot_id": "fixture-snapshot-aapl", "version": 1, "delivery": "in-app-only", "created_at": observed, "updated_at": observed},
            {"resource_id": "fixture-alert-rule-source", "watchlist_id": "fixture-daily", "symbol": "BTCUSDT", "asset_class": "crypto", "rule_type": "source_degradation", "metric": "source_status", "operator": "degrades_to_or_below", "threshold": "stale", "threshold_unit": "status", "severity": "watch", "state": "paused", "state_reason": "stopped-manually", "schedule": {"frequency": "1h", "frequency_minutes": 60, "session_policy": "continuous", "next_due_at": None, "calendar_status": "continuous"}, "cooldown_minutes": 120, "expires_at": None, "last_evaluated_at": None, "last_triggered_at": None, "last_snapshot_id": None, "version": 2, "delivery": "in-app-only", "created_at": observed, "updated_at": observed},
        ],
        "due_plan": {"planned_at": observed, "due": [], "not_due": [], "due_count": 0, "bounded_count": 2, "maximum_rules": MAX_ALERT_RULES, "provider_call_count": 0},
        "triggers": [trigger],
        "evaluations": [{"run_id": "fixture-alert-run", "status": "completed", "mode": "manual", "due_count": 1, "evaluated_count": 1, "triggered_count": 1, "deduped_count": 0, "data_gap_count": 0, "quota_blocked_count": 0, "provider_call_count": 0, "source_clock": {"observed_at": observed, "retrieved_at": observed, "evaluated_at": observed}, "detail": {"market_provider_calls": 0}, "started_at": observed, "completed_at": observed, "duration_ms": 4, "idempotent_replay": False}],
        "worker": {"enabled": False, "state": "stopped", "reason": "explicit-opt-in-required", "view_starts_worker": False, "observation_jobs_enabled": False, "evaluation_source": "stored-phase6n-observations", "last_heartbeat_at": None, "last_evaluation_run_id": None, "restart_count": 0, "manual_run_available": True, "provider_call_count": 0, "caveat": "Fixture; no worker or provider was contacted."},
        "clock_legend": {"observation": "Saved source clock.", "retrieval": "Provider retrieval clock.", "evaluation": "Rule evaluation clock.", "trigger": "Persisted trigger clock.", "review": "User review clock."},
        "delivery_channels": {"in_app": "available", "email": "unavailable", "sms": "unavailable", "push": "unavailable", "webhook": "unavailable"},
        "bounds": {"maximum_rules": MAX_ALERT_RULES, "maximum_trigger_history": MAX_ALERT_TRIGGERS, "maximum_observation_symbols": 5, "maximum_observation_provider_calls": 16, "maximum_provider_concurrency": 2},
        "hosted_readiness": {"status": "unavailable", "migration": "phase6o-required", "rls_ab_conformance": "not-run", "recovery_conformance": "not-run", "hosted_scheduler": "unavailable", "caveat": "Fictional local fixture; no hosted claim."},
        "legacy_preview": {"status": "deprecated-compatibility", "routes_retained": True, "replacement": "/api/account/alert-manager"},
        "state_catalog": ["no-rules", "active-due", "active-not-due", "triggered", "cooldown-deduped", "paused", "expired", "cancelled", "deleted", "quota-blocked", "partial-lkg", "provider-unavailable", "worker-stopped", "worker-offline", "worker-restarted", "conflict", "hosted-unavailable"],
        "research_only": True,
        "not_financial_advice": True,
    }
