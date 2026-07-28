from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .identity_tenancy import _require_authenticated, public_account_payload
from .research_snapshot_diff import build_change_alert_preview, build_research_snapshot_diff
from .research_workspace_db import execute_query, get_connection, json_dumps, json_loads, new_id
from .watchlist_desk import list_materialization_jobs


TENANT_RESEARCH_DESK_VERSION = "tenant_research_desk.v1"
MAX_IMPORT_CANDIDATES = 25
MAX_TENANT_WATCHLISTS = 20
MAX_INBOX_ITEMS = 100
INBOX_RETENTION_DAYS = 90
CONSENT_RETENTION_DAYS = 365
_SEVERITY_RANK = {"info": 0, "material": 1, "high": 2, "critical": 3}
_IDENTITY_FIELDS = {"tenant_id", "user_id", "owner_user_id", "role", "plan"}
_INBOX_STATES = {"new", "reviewed", "acknowledged"}
_DEGRADED_SOURCE_STATES = {"error", "forbidden", "missing-key", "rate-limited", "stale", "unavailable"}


class TenantResearchConflict(RuntimeError):
    def __init__(self, current_version: int):
        super().__init__("Tenant research resource version conflict.")
        self.current_version = int(current_version)


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    return (current if current.tzinfo else current.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return _now(value).replace(microsecond=0).isoformat()


def _hash(value: Any, *, prefix: str = "") -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:20]
    return f"{prefix}{digest}"


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return _now(parsed)
    except (TypeError, ValueError):
        return None


def validate_import_body(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError("Import body must be an object.")
    if _IDENTITY_FIELDS.intersection(body):
        raise ValueError("Tenant and user identity are server-derived.")
    if body.get("consent") is not True:
        raise ValueError("Explicit import consent is required.")
    preview_id = str(body.get("preview_id") or "").strip()
    if not preview_id.startswith("preview_") or len(preview_id) > 80:
        raise ValueError("A valid preview_id is required.")
    candidate_ids = body.get("candidate_ids")
    if not isinstance(candidate_ids, list) or not candidate_ids or len(candidate_ids) > MAX_IMPORT_CANDIDATES:
        raise ValueError("candidate_ids must be a non-empty bounded list.")
    normalized_candidates = list(dict.fromkeys(str(value or "").strip() for value in candidate_ids))
    if any(not value.startswith("candidate_") or len(value) > 80 for value in normalized_candidates):
        raise ValueError("Invalid candidate_id.")
    idempotency_key = str(body.get("idempotency_key") or "").strip()
    if not 8 <= len(idempotency_key) <= 128:
        raise ValueError("idempotency_key must contain 8 to 128 characters.")
    expected_version = body.get("expected_version")
    if not isinstance(expected_version, int) or expected_version < 0:
        raise ValueError("expected_version must be a non-negative integer.")
    name = " ".join(str(body.get("destination_name") or "Account watchlist").split())[:80]
    if not name:
        raise ValueError("destination_name is required.")
    return {
        "preview_id": preview_id,
        "candidate_ids": normalized_candidates,
        "consent": True,
        "idempotency_key": idempotency_key,
        "expected_version": expected_version,
        "destination_name": name,
    }


def build_attention_queue(inbox: list[dict[str, Any]], *, limit: int = 25) -> dict[str, Any]:
    state_weight = {"new": 100, "reviewed": 25, "acknowledged": 0, "expired": -20}
    severity_weight = {"critical": 60, "high": 40, "material": 25, "info": 0}
    rows: list[dict[str, Any]] = []
    for item in inbox or []:
        if not isinstance(item, dict):
            continue
        state = str(item.get("state") or "new").lower()
        severity = str(item.get("severity") or "info").lower()
        source_status = str(item.get("source_status") or "unavailable").lower()
        degraded = source_status in _DEGRADED_SOURCE_STATES
        score = state_weight.get(state, 0) + severity_weight.get(severity, 0) + (20 if degraded else 0)
        reasons = []
        if state == "new":
            reasons.append("unreviewed")
        if severity in {"material", "high", "critical"}:
            reasons.append(severity)
        if degraded:
            reasons.append("source-degraded")
        rows.append({**item, "attention_score": score, "attention_reason": reasons or ["history"]})
    rows.sort(
        key=lambda row: (
            -int(row.get("attention_score") or 0),
            str(row.get("created_at") or ""),
            str(row.get("resource_id") or ""),
        )
    )
    bounded = rows[: max(1, min(int(limit), 25))]
    return public_account_payload(
        {
            "items": bounded,
            "attention_count": sum(
                1
                for row in rows
                if str(row.get("state")) == "new" and _SEVERITY_RANK.get(str(row.get("severity")), 0) >= _SEVERITY_RANK["material"]
            ),
            "degraded_source_count": sum(1 for row in rows if str(row.get("source_status") or "").lower() in _DEGRADED_SOURCE_STATES),
            "total_count": len(rows),
            "delivery": "in-app-triage-only",
            "ranking": "state + severity + source degradation",
            "provider_call_count": 0,
            "caveat": "Priority is deterministic research triage, not a recommendation or autonomous alert.",
        }
    )


class TenantResearchDeskStore:
    def __init__(self, account_db_path: str | Path | None = None, local_db_path: str | Path | None = None):
        self.account_db_path = account_db_path
        self.local_db_path = local_db_path

    def summary(self, context: dict[str, Any]) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        counts: dict[str, int] = {}
        for key, table in (("watchlist_count", "tenant_watchlists"), ("inbox_count", "tenant_inbox_items")):
            row = execute_query(
                f"SELECT COUNT(*) AS count FROM {table} WHERE tenant_id = ?" + (" AND active = 1" if table == "tenant_watchlists" else ""),
                (tenant_id,), fetch=True, one=True, db_path=self.account_db_path,
            )
            counts[key] = int((row or {}).get("count") or 0)
        unread = execute_query(
            "SELECT COUNT(*) AS count FROM tenant_inbox_items WHERE tenant_id = ? AND state = 'new'",
            (tenant_id,), fetch=True, one=True, db_path=self.account_db_path,
        )
        return {**counts, "unread_count": int((unread or {}).get("count") or 0), "provider_call_count": 0}

    def preview_import(self, context: dict[str, Any], *, source_list_id: str = "primary", limit: int = 25) -> dict[str, Any]:
        _require_authenticated(context)
        bounded = max(1, min(int(limit), MAX_IMPORT_CANDIDATES))
        source_id = str(source_list_id or "").strip().lower()
        collection = execute_query(
            "SELECT list_id, name, updated_at FROM watchlist_collections WHERE list_id = ? AND active = 1",
            (source_id,), fetch=True, one=True, db_path=self.local_db_path,
        )
        if not collection:
            raise ValueError("Local watchlist source not found.")
        rows = execute_query(
            """
            SELECT symbol, display_name, asset_class, exchange, position, updated_at
            FROM watchlist_items
            WHERE watchlist_id = ? AND active = 1 AND symbol IS NOT NULL AND trim(symbol) != ''
            ORDER BY position, symbol LIMIT ?
            """,
            (source_id, bounded), fetch=True, db_path=self.local_db_path,
        )
        jobs = list_materialization_jobs(source_id, limit=1, completed_only=True, db_path=self.local_db_path)
        snapshots = {str(row.get("symbol") or "").upper(): row for row in ((jobs[0].get("rows") if jobs else []) or [])}
        candidates = []
        for row in rows or []:
            symbol = str(row.get("symbol") or "").upper()
            snapshot = snapshots.get(symbol, {})
            quote = snapshot.get("quote") if isinstance(snapshot.get("quote"), dict) else {}
            evidence = {
                "provider": snapshot.get("provider") or quote.get("provider") or "local-saved-snapshot",
                "source_url": snapshot.get("source_url") or quote.get("source_url") or "",
                "source_status": snapshot.get("source_status") or quote.get("source_status") or "unavailable",
                "observed_at": quote.get("observed_at"),
                "retrieved_at": snapshot.get("fetched_at") or quote.get("retrieved_at"),
                "caveat": "Imported from a saved local observation; no provider was contacted during preview.",
            }
            candidates.append(
                {
                    "candidate_id": _hash({"list": source_id, "symbol": symbol}, prefix="candidate_"),
                    "symbol": symbol,
                    "display_name": str(row.get("display_name") or symbol),
                    "asset_class": str(row.get("asset_class") or ""),
                    "exchange": str(row.get("exchange") or ""),
                    "position": int(row.get("position") or 0),
                    "evidence": evidence,
                }
            )
        source_fingerprint = _hash({"list": source_id, "updated_at": collection.get("updated_at"), "candidates": candidates})
        preview_id = _hash({"source": source_id, "fingerprint": source_fingerprint}, prefix="preview_")
        return public_account_payload(
            {
                "preview_id": preview_id,
                "source_list_id": source_id,
                "source_name": collection.get("name") or source_id,
                "source_fingerprint": source_fingerprint,
                "candidate_count": len(candidates),
                "candidates": candidates,
                "bounded_limit": bounded,
                "excluded_fields": ["metadata_json", "watch_reason"],
                "provider_call_count": 0,
                "read_only": True,
                "consent_required": True,
                "caveat": "Preview reads bounded local saved data and does not copy private notes.",
            }
        )

    def _resolve_preview(self, context: dict[str, Any], preview_id: str) -> dict[str, Any]:
        collections = execute_query(
            "SELECT list_id FROM watchlist_collections WHERE active = 1 ORDER BY position, list_id LIMIT 50",
            fetch=True, db_path=self.local_db_path,
        )
        for row in collections or []:
            preview = self.preview_import(context, source_list_id=str(row.get("list_id") or ""))
            if preview["preview_id"] == preview_id:
                return preview
        raise ValueError("Import preview is missing or no longer current.")

    def confirm_import(self, context: dict[str, Any], body: Any) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        validated = validate_import_body(body)
        request_fingerprint = _hash({key: validated[key] for key in ("preview_id", "candidate_ids", "destination_name")})
        receipt = execute_query(
            "SELECT * FROM tenant_import_receipts WHERE tenant_id = ? AND idempotency_key = ?",
            (tenant_id, validated["idempotency_key"]), fetch=True, one=True, db_path=self.account_db_path,
        )
        if receipt:
            if receipt.get("request_fingerprint") != request_fingerprint:
                raise ValueError("Idempotency key was already used for a different import request.")
            result = json_loads(receipt.get("result_json"), {})
            return {**result, "status": "deduped"}
        preview = self._resolve_preview(context, validated["preview_id"])
        selected_ids = set(validated["candidate_ids"])
        selected = [row for row in preview["candidates"] if row["candidate_id"] in selected_ids]
        if len(selected) != len(selected_ids):
            raise ValueError("One or more import candidates are invalid or stale.")
        source_key = f"local:{preview['source_list_id']}"
        existing = execute_query(
            "SELECT * FROM tenant_watchlists WHERE tenant_id = ? AND source_key = ?",
            (tenant_id, source_key), fetch=True, one=True, db_path=self.account_db_path,
        )
        current_version = int((existing or {}).get("version") or 0)
        if current_version != validated["expected_version"]:
            raise TenantResearchConflict(current_version)
        count = execute_query(
            "SELECT COUNT(*) AS count FROM tenant_watchlists WHERE tenant_id = ? AND active = 1",
            (tenant_id,), fetch=True, one=True, db_path=self.account_db_path,
        )
        if not existing and int((count or {}).get("count") or 0) >= MAX_TENANT_WATCHLISTS:
            raise ValueError("Tenant watchlist limit reached.")
        timestamp = _iso()
        watchlist_id = str((existing or {}).get("resource_id") or new_id("twl"))
        version = current_version + 1
        with get_connection(self.account_db_path) as conn:
            if existing:
                conn.execute(
                    "UPDATE tenant_watchlists SET owner_user_id=?, name=?, source_fingerprint=?, version=?, active=1, updated_at=? WHERE tenant_id=? AND resource_id=?",
                    (user_id, validated["destination_name"], preview["source_fingerprint"], version, timestamp, tenant_id, watchlist_id),
                )
                conn.execute("DELETE FROM tenant_watchlist_items WHERE tenant_id=? AND watchlist_resource_id=?", (tenant_id, watchlist_id))
            else:
                conn.execute(
                    "INSERT INTO tenant_watchlists (resource_id, tenant_id, owner_user_id, name, source_key, source_fingerprint, version, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                    (watchlist_id, tenant_id, user_id, validated["destination_name"], source_key, preview["source_fingerprint"], version, timestamp, timestamp),
                )
            for candidate in selected:
                evidence = candidate.get("evidence") or {}
                conn.execute(
                    """
                    INSERT INTO tenant_watchlist_items (
                        resource_id, tenant_id, watchlist_resource_id, symbol, asset_class, display_name,
                        exchange, position, provider, source_url, source_status, observed_at, retrieved_at,
                        evidence_json, version, active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                    """,
                    (
                        new_id("twi"), tenant_id, watchlist_id, candidate["symbol"], candidate["asset_class"],
                        candidate["display_name"], candidate["exchange"], candidate["position"],
                        evidence.get("provider") or "", evidence.get("source_url") or "",
                        evidence.get("source_status") or "unavailable", evidence.get("observed_at"),
                        evidence.get("retrieved_at"), json_dumps(evidence), timestamp, timestamp,
                    ),
                )
            watchlist = self._get_watchlist_with_conn(conn, tenant_id, watchlist_id)
            result = {"status": "imported", "watchlist": watchlist, "selected_count": len(selected), "provider_call_count": 0}
            conn.execute(
                "INSERT INTO tenant_import_receipts (receipt_id, tenant_id, owner_user_id, idempotency_key, request_fingerprint, preview_id, watchlist_resource_id, selected_count, excluded_fields_json, result_json, consented_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id("tir"), tenant_id, user_id, validated["idempotency_key"], request_fingerprint, preview["preview_id"], watchlist_id, len(selected), json_dumps(preview["excluded_fields"]), json_dumps(result), timestamp),
            )
        return public_account_payload(result)

    def cancel_import(self, context: dict[str, Any], *, preview_id: str) -> dict[str, Any]:
        _require_authenticated(context)
        if not str(preview_id or "").startswith("preview_"):
            raise ValueError("Invalid preview_id.")
        return {"status": "canceled", "preview_id": preview_id, "mutated": False, "provider_call_count": 0}

    def _get_watchlist_with_conn(self, conn: Any, tenant_id: str, resource_id: str) -> dict[str, Any] | None:
        row = conn.execute(
            "SELECT * FROM tenant_watchlists WHERE tenant_id=? AND resource_id=? AND active=1",
            (tenant_id, resource_id),
        ).fetchone()
        if not row:
            return None
        items = conn.execute(
            "SELECT * FROM tenant_watchlist_items WHERE tenant_id=? AND watchlist_resource_id=? AND active=1 ORDER BY position, symbol",
            (tenant_id, resource_id),
        ).fetchall()
        return self._public_watchlist(dict(row), [dict(item) for item in items])

    def _public_watchlist(self, row: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
        public_items = []
        for item in items:
            evidence = json_loads(item.get("evidence_json"), {})
            query = urlencode(
                {
                    "view": "analyst-workspace", "symbol": item.get("symbol"),
                    "asset_class": item.get("asset_class") or "equity", "account_item": item.get("resource_id"),
                    "originView": "watchlist-desk", "originState": "account-research",
                    "accountWatchlist": row.get("resource_id"),
                }
            )
            public_items.append(
                {
                    "resource_id": item.get("resource_id"), "symbol": item.get("symbol"),
                    "display_name": item.get("display_name"), "asset_class": item.get("asset_class"),
                    "exchange": item.get("exchange"), "position": int(item.get("position") or 0),
                    "provider": item.get("provider"), "source_url": item.get("source_url"),
                    "source_status": item.get("source_status"), "observed_at": item.get("observed_at"),
                    "retrieved_at": item.get("retrieved_at"), "evidence": evidence,
                    "research_href": f"/?{query}", "version": int(item.get("version") or 1),
                }
            )
        return public_account_payload(
            {
                "resource_id": row.get("resource_id"), "name": row.get("name"),
                "version": int(row.get("version") or 1), "item_count": len(public_items), "items": public_items,
                "source_status": "saved-account-copy", "updated_at": row.get("updated_at"),
                "caveat": "Account-owned copy of selected local saved observations; no background refresh is implied.",
            }
        )

    def get_watchlist(self, context: dict[str, Any], resource_id: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        with get_connection(self.account_db_path) as conn:
            return self._get_watchlist_with_conn(conn, tenant_id, str(resource_id or ""))

    def list_watchlists(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        rows = execute_query(
            "SELECT resource_id FROM tenant_watchlists WHERE tenant_id=? AND active=1 ORDER BY updated_at DESC LIMIT ?",
            (tenant_id, MAX_TENANT_WATCHLISTS), fetch=True, db_path=self.account_db_path,
        )
        return [watchlist for row in rows or [] if (watchlist := self.get_watchlist(context, str(row.get("resource_id"))))]

    def delete_watchlist(self, context: dict[str, Any], resource_id: str, *, expected_version: int) -> bool:
        tenant_id, _ = _require_authenticated(context)
        existing = execute_query(
            "SELECT version FROM tenant_watchlists WHERE tenant_id=? AND resource_id=? AND active=1",
            (tenant_id, resource_id), fetch=True, one=True, db_path=self.account_db_path,
        )
        if not existing:
            return False
        if int(existing.get("version") or 0) != int(expected_version):
            raise TenantResearchConflict(int(existing.get("version") or 0))
        with get_connection(self.account_db_path) as conn:
            conn.execute("DELETE FROM tenant_inbox_items WHERE tenant_id=? AND watchlist_resource_id=?", (tenant_id, resource_id))
            conn.execute("DELETE FROM tenant_alert_rules WHERE tenant_id=? AND watchlist_resource_id=?", (tenant_id, resource_id))
            conn.execute("DELETE FROM tenant_import_receipts WHERE tenant_id=? AND watchlist_resource_id=?", (tenant_id, resource_id))
            conn.execute("DELETE FROM tenant_watchlist_items WHERE tenant_id=? AND watchlist_resource_id=?", (tenant_id, resource_id))
            conn.execute("DELETE FROM tenant_watchlists WHERE tenant_id=? AND resource_id=?", (tenant_id, resource_id))
        return True

    def configure_rule(
        self, context: dict[str, Any], watchlist_id: str, *, enabled: bool,
        minimum_severity: str = "material", cooldown_minutes: int = 60,
        expected_version: int = 0, expires_at: str | None = None, now: datetime | None = None,
    ) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        if not self.get_watchlist(context, watchlist_id):
            raise KeyError("Tenant watchlist not found.")
        severity = str(minimum_severity or "material").lower()
        if severity not in _SEVERITY_RANK:
            raise ValueError("Invalid minimum severity.")
        cooldown = max(0, min(int(cooldown_minutes), 10_080))
        if expires_at and not _parse_time(expires_at):
            raise ValueError("Invalid expiry timestamp.")
        existing = execute_query(
            "SELECT * FROM tenant_alert_rules WHERE tenant_id=? AND watchlist_resource_id=?",
            (tenant_id, watchlist_id), fetch=True, one=True, db_path=self.account_db_path,
        )
        current_version = int((existing or {}).get("version") or 0)
        if current_version != int(expected_version):
            raise TenantResearchConflict(current_version)
        timestamp = _iso(now)
        rule_id = str((existing or {}).get("resource_id") or new_id("tar"))
        version = current_version + 1
        if existing:
            execute_query(
                "UPDATE tenant_alert_rules SET owner_user_id=?, enabled=?, minimum_severity=?, cooldown_minutes=?, expires_at=?, version=?, updated_at=? WHERE tenant_id=? AND resource_id=?",
                (user_id, 1 if enabled else 0, severity, cooldown, expires_at, version, timestamp, tenant_id, rule_id), db_path=self.account_db_path,
            )
        else:
            execute_query(
                "INSERT INTO tenant_alert_rules (resource_id, tenant_id, owner_user_id, watchlist_resource_id, enabled, minimum_severity, cooldown_minutes, expires_at, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rule_id, tenant_id, user_id, watchlist_id, 1 if enabled else 0, severity, cooldown, expires_at, version, timestamp, timestamp), db_path=self.account_db_path,
            )
        rule = self._rule(context, watchlist_id)
        return rule or {}

    def _rule(self, context: dict[str, Any], watchlist_id: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        row = execute_query(
            "SELECT * FROM tenant_alert_rules WHERE tenant_id=? AND watchlist_resource_id=?",
            (tenant_id, watchlist_id), fetch=True, one=True, db_path=self.account_db_path,
        )
        if not row:
            return None
        return public_account_payload(
            {
                "resource_id": row.get("resource_id"), "watchlist_resource_id": row.get("watchlist_resource_id"),
                "enabled": bool(row.get("enabled")), "minimum_severity": row.get("minimum_severity"),
                "cooldown_minutes": int(row.get("cooldown_minutes") or 0), "expires_at": row.get("expires_at"),
                "last_triggered_at": row.get("last_triggered_at"), "version": int(row.get("version") or 1),
                "delivery": "in-app-only", "hosted_delivery": "unavailable", "updated_at": row.get("updated_at"),
            }
        )

    def scan_inbox(self, context: dict[str, Any], watchlist_id: str, *, now: datetime | None = None, kill_switch: bool = False) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        watchlist = execute_query(
            "SELECT * FROM tenant_watchlists WHERE tenant_id=? AND resource_id=? AND active=1",
            (tenant_id, watchlist_id), fetch=True, one=True, db_path=self.account_db_path,
        )
        if not watchlist:
            raise KeyError("Tenant watchlist not found.")
        rule = execute_query(
            "SELECT * FROM tenant_alert_rules WHERE tenant_id=? AND watchlist_resource_id=?",
            (tenant_id, watchlist_id), fetch=True, one=True, db_path=self.account_db_path,
        )
        base = {"provider_call_count": 0, "stored_count": 0, "delivery": "in-app-only", "hosted_delivery": "unavailable"}
        if not rule or not bool(rule.get("enabled")):
            return {**base, "status": "disabled"}
        if kill_switch:
            return {**base, "status": "suppressed", "kill_switch_engaged": True}
        current_time = _now(now)
        expiry = _parse_time(rule.get("expires_at"))
        if expiry and expiry < current_time:
            return {**base, "status": "expired"}
        source_list_id = str(watchlist.get("source_key") or "").removeprefix("local:")
        jobs = list_materialization_jobs(source_list_id, limit=20, completed_only=True, db_path=self.local_db_path)
        successes = [row for row in jobs if row.get("rows")]
        diff = build_research_snapshot_diff(successes[1] if len(successes) > 1 else None, successes[0] if successes else None, now=current_time)
        imported = execute_query(
            "SELECT symbol FROM tenant_watchlist_items WHERE tenant_id=? AND watchlist_resource_id=? AND active=1",
            (tenant_id, watchlist_id), fetch=True, db_path=self.account_db_path,
        )
        symbols = {str(row.get("symbol") or "").upper() for row in imported or []}
        diff["changes"] = [row for row in diff.get("changes") or [] if str(row.get("symbol") or "").upper() in symbols]
        diff["summary"] = {**(diff.get("summary") or {}), "change_count": len(diff["changes"])}
        existing = execute_query(
            "SELECT * FROM tenant_inbox_items WHERE tenant_id=? AND watchlist_resource_id=? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, watchlist_id, MAX_INBOX_ITEMS), fetch=True, db_path=self.account_db_path,
        )
        adapter_rule = {
            "alert_id": rule.get("resource_id"), "active": bool(rule.get("enabled")),
            "threshold": rule.get("minimum_severity"), "cooldown_minutes": rule.get("cooldown_minutes"),
            "expires_at": rule.get("expires_at"), "last_triggered_at": rule.get("last_triggered_at"),
            "metadata_json": {"minimum_severity": rule.get("minimum_severity")},
        }
        adapter_events = [
            {"event_id": row.get("resource_id"), "metadata_json": {"fingerprint": row.get("dedupe_key"), "acknowledged_at": row.get("acknowledged_at")}}
            for row in existing or []
        ]
        preview = build_change_alert_preview(diff, rule=adapter_rule, events=adapter_events, now=current_time)
        stored = 0
        timestamp = _iso(current_time)
        with get_connection(self.account_db_path) as conn:
            for candidate in preview.get("candidates") or []:
                if candidate.get("status") != "preview-ready":
                    continue
                evidence = candidate.get("evidence") if isinstance(candidate.get("evidence"), dict) else {}
                after = evidence.get("after") if isinstance(evidence.get("after"), dict) else {}
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO tenant_inbox_items (
                        resource_id, tenant_id, owner_user_id, watchlist_resource_id, rule_resource_id,
                        dedupe_key, symbol, change_id, change_type, state, severity, title, summary,
                        evidence_json, source_status, observed_at, retrieved_at, expires_at, version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        new_id("tii"), tenant_id, user_id, watchlist_id, rule.get("resource_id"), candidate.get("fingerprint"),
                        candidate.get("symbol") or "", candidate.get("change_id") or "", candidate.get("change_type") or "change",
                        candidate.get("severity") or "material", f"{candidate.get('symbol') or 'Asset'} saved change",
                        candidate.get("observation") or "Saved observation changed.", json_dumps(evidence),
                        after.get("source_status") or diff.get("source_status") or "unavailable",
                        after.get("fetched_at"), after.get("fetched_at"),
                        _iso(current_time + timedelta(days=INBOX_RETENTION_DAYS)), timestamp, timestamp,
                    ),
                )
                stored += max(0, int(cursor.rowcount or 0))
            if stored:
                conn.execute(
                    "UPDATE tenant_alert_rules SET last_triggered_at=?, updated_at=? WHERE tenant_id=? AND resource_id=?",
                    (timestamp, timestamp, tenant_id, rule.get("resource_id")),
                )
        status = "stored" if stored else str(preview.get("status") or "no-candidates")
        return {**base, "status": status, "stored_count": stored, "candidate_count": int(preview.get("candidate_count") or 0), "source_status": diff.get("source_status")}

    def _public_inbox(self, row: dict[str, Any]) -> dict[str, Any]:
        query = urlencode(
            {
                "view": "analyst-workspace", "symbol": row.get("symbol"), "change": row.get("change_id"),
                "inbox": row.get("resource_id"), "originView": "watchlist-desk",
                "originState": "account-research", "accountWatchlist": row.get("watchlist_resource_id"),
            }
        )
        state = str(row.get("state") or "new")
        expiry = _parse_time(row.get("expires_at"))
        if expiry and expiry < _now() and state != "acknowledged":
            state = "expired"
        return public_account_payload(
            {
                "resource_id": row.get("resource_id"), "watchlist_resource_id": row.get("watchlist_resource_id"),
                "symbol": row.get("symbol"), "change_id": row.get("change_id"), "change_type": row.get("change_type"),
                "state": state, "severity": row.get("severity"), "title": row.get("title"),
                "summary": row.get("summary"), "evidence": json_loads(row.get("evidence_json"), {}),
                "source_status": row.get("source_status"), "observed_at": row.get("observed_at"),
                "retrieved_at": row.get("retrieved_at"), "expires_at": row.get("expires_at"),
                "reviewed_at": row.get("reviewed_at"), "acknowledged_at": row.get("acknowledged_at"),
                "version": int(row.get("version") or 1), "research_href": f"/?{query}",
                "delivery": "in-app-only",
                "delivery_status": "suppressed" if state == "expired" else "delivery-unavailable",
                "created_at": row.get("created_at"), "updated_at": row.get("updated_at"),
            }
        )

    def list_inbox(self, context: dict[str, Any], *, now: datetime | None = None) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        rows = execute_query(
            "SELECT * FROM tenant_inbox_items WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, MAX_INBOX_ITEMS), fetch=True, db_path=self.account_db_path,
        )
        del now
        return [self._public_inbox(row) for row in rows or []]

    def get_inbox_item(self, context: dict[str, Any], resource_id: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        row = execute_query(
            "SELECT * FROM tenant_inbox_items WHERE tenant_id=? AND resource_id=?",
            (tenant_id, resource_id), fetch=True, one=True, db_path=self.account_db_path,
        )
        return self._public_inbox(row) if row else None

    def update_inbox_state(self, context: dict[str, Any], resource_id: str, *, state: str, expected_version: int, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        normalized = str(state or "").lower()
        if normalized not in _INBOX_STATES:
            raise ValueError("Invalid inbox state.")
        existing = execute_query(
            "SELECT * FROM tenant_inbox_items WHERE tenant_id=? AND resource_id=?",
            (tenant_id, resource_id), fetch=True, one=True, db_path=self.account_db_path,
        )
        if not existing:
            raise KeyError("Tenant inbox item not found.")
        current_version = int(existing.get("version") or 0)
        if current_version != int(expected_version):
            raise TenantResearchConflict(current_version)
        current_state = str(existing.get("state") or "new")
        allowed_transitions = {
            "new": {"new", "reviewed", "acknowledged"},
            "reviewed": {"reviewed", "acknowledged"},
            "acknowledged": {"acknowledged"},
        }
        if normalized not in allowed_transitions.get(current_state, set()):
            raise ValueError("Inbox state cannot move backward.")
        timestamp = _iso(now)
        reviewed = timestamp if normalized in {"reviewed", "acknowledged"} else existing.get("reviewed_at")
        acknowledged = timestamp if normalized == "acknowledged" else existing.get("acknowledged_at")
        execute_query(
            "UPDATE tenant_inbox_items SET state=?, reviewed_at=?, acknowledged_at=?, version=?, updated_at=? WHERE tenant_id=? AND resource_id=?",
            (normalized, reviewed, acknowledged, current_version + 1, timestamp, tenant_id, resource_id), db_path=self.account_db_path,
        )
        return self.get_inbox_item(context, resource_id) or {}

    def export(self, context: dict[str, Any]) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        rules = execute_query(
            "SELECT watchlist_resource_id FROM tenant_alert_rules WHERE tenant_id=? ORDER BY updated_at DESC LIMIT ?",
            (tenant_id, MAX_TENANT_WATCHLISTS), fetch=True, db_path=self.account_db_path,
        )
        receipts = execute_query(
            "SELECT receipt_id, preview_id, watchlist_resource_id, selected_count, excluded_fields_json, consented_at FROM tenant_import_receipts WHERE tenant_id=? ORDER BY consented_at DESC LIMIT 100",
            (tenant_id,), fetch=True, db_path=self.account_db_path,
        )
        public_receipts = [
            {
                "receipt_id": row.get("receipt_id"), "preview_id": row.get("preview_id"),
                "watchlist_resource_id": row.get("watchlist_resource_id"),
                "selected_count": int(row.get("selected_count") or 0),
                "excluded_fields": json_loads(row.get("excluded_fields_json"), []),
                "consented_at": row.get("consented_at"),
                "retention_days": CONSENT_RETENTION_DAYS,
            }
            for row in receipts or []
        ]
        return public_account_payload(
            {
                "tenant_research_desk_version": TENANT_RESEARCH_DESK_VERSION,
                "watchlists": self.list_watchlists(context),
                "rules": [rule for row in rules or [] if (rule := self._rule(context, str(row.get("watchlist_resource_id"))))],
                "inbox": self.list_inbox(context),
                "consent_receipts": public_receipts,
                "exported_at": _iso(), "bounded": True, "provider_call_count": 0,
                "retention": {"inbox_days": INBOX_RETENTION_DAYS, "consent_receipt_days": CONSENT_RETENTION_DAYS},
                "caveat": "Account export excludes local private notes, session identity, and provider secrets.",
            }
        )

    def build_contract(self, context: dict[str, Any]) -> dict[str, Any]:
        exported = self.export(context)
        attention = build_attention_queue(exported["inbox"])
        summary = self.summary(context)
        summary["attention_count"] = attention["attention_count"]
        summary["degraded_source_count"] = attention["degraded_source_count"]
        return public_account_payload(
            {
                "tenant_research_desk_version": TENANT_RESEARCH_DESK_VERSION,
                "summary": summary, "watchlists": exported["watchlists"],
                "rules": exported["rules"], "inbox": exported["inbox"], "attention": attention,
                "readiness": {"local_account_store": "available", "hosted_persistence": "unavailable", "external_delivery": "unavailable"},
                "provider_call_count": 0,
                "caveat": "Process-local account research is a development surface, not hosted authentication or delivery.",
                "not_financial_advice": True,
            }
        )
