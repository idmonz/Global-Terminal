from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .identity_tenancy import _require_authenticated, public_account_payload
from .research_workspace_db import execute_query, json_dumps, json_loads, new_id
from .tenant_research_persistence import (
    MAX_SYNC_BYTES,
    MAX_SYNC_RESOURCES,
    HostedPersistenceUnavailable,
    TenantResearchPersistence,
    normalize_sync_snapshot,
)


MAX_OFFLINE_MUTATIONS = 100
MAX_REPLAY_BATCH = 10
MAX_RETRY_ATTEMPTS = 5
_CLIENT_IDENTITY_FIELDS = {"tenant_id", "user_id", "owner_user_id", "role", "plan"}


def _iso(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    if not current.tzinfo:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _indexed(snapshot: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row.get("resource_type") or "record"), str(row.get("resource_id") or "")): row
        for row in (snapshot or {}).get("resources") or []
        if isinstance(row, dict) and row.get("resource_id")
    }


def build_reconciliation_plan(local_snapshot: dict[str, Any], remote_snapshot: dict[str, Any]) -> dict[str, Any]:
    local = _indexed(normalize_sync_snapshot(local_snapshot))
    remote = _indexed(normalize_sync_snapshot(remote_snapshot))
    counts = {state: 0 for state in ("same-version", "local-newer", "remote-newer", "conflict", "deletion")}
    items: list[dict[str, Any]] = []
    for key in sorted(set(local) | set(remote)):
        local_row = local.get(key)
        remote_row = remote.get(key)
        if local_row and bool(local_row.get("deleted")):
            state = "deletion"
            action = "confirm-local-deletion"
        elif remote_row and bool(remote_row.get("deleted")):
            state = "deletion"
            action = "confirm-remote-deletion"
        elif local_row is None:
            state = "remote-newer"
            action = "review-download"
        elif remote_row is None:
            state = "local-newer"
            action = "review-upload"
        else:
            local_version = int(local_row.get("version") or 0)
            remote_version = int(remote_row.get("version") or 0)
            if local_version > remote_version:
                state, action = "local-newer", "review-upload"
            elif remote_version > local_version:
                state, action = "remote-newer", "review-download"
            elif str(local_row.get("fingerprint")) == str(remote_row.get("fingerprint")):
                state, action = "same-version", "none"
            else:
                state, action = "conflict", "manual-resolution"
        counts[state] += 1
        items.append(
            {
                "resource_type": key[0],
                "resource_id": key[1],
                "state": state,
                "action": action,
                "local_version": int((local_row or {}).get("version") or 0),
                "remote_version": int((remote_row or {}).get("version") or 0),
            }
        )
    return {
        "strategy": "explicit-resolution",
        "items": items,
        "counts": counts,
        "requires_user_resolution": bool(counts["conflict"] or counts["deletion"]),
        "silent_last_write_wins": False,
        "provider_call_count": 0,
    }


def validate_first_sync_body(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError("Sync body must be an object.")
    if _CLIENT_IDENTITY_FIELDS.intersection(body):
        raise ValueError("Tenant and user identity are server-derived.")
    if body.get("consent") is not True:
        raise ValueError("Explicit first-sync consent is required.")
    key = str(body.get("idempotency_key") or "").strip()
    if not 8 <= len(key) <= 128:
        raise ValueError("idempotency_key must contain 8 to 128 characters.")
    return {"consent": True, "idempotency_key": key}


class TenantResearchSyncCoordinator:
    def __init__(
        self,
        *,
        db_path: str | Path | None,
        local: TenantResearchPersistence,
        hosted: TenantResearchPersistence,
    ):
        self.db_path = db_path
        self.local = local
        self.hosted = hosted

    def _audit(
        self,
        tenant_id: str,
        event_type: str,
        status: str,
        *,
        mutation_id: str = "",
        detail: dict[str, Any] | None = None,
    ) -> None:
        safe_detail = {
            key: value
            for key, value in (detail or {}).items()
            if key not in _CLIENT_IDENTITY_FIELDS and "token" not in key.lower() and "secret" not in key.lower()
        }
        execute_query(
            """
            INSERT INTO tenant_sync_audit (
                event_id, tenant_id, event_type, status, mutation_id, detail_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id("tsa"), tenant_id, event_type[:48], status[:32], mutation_id[:80], json_dumps(safe_detail), _iso()),
            db_path=self.db_path,
        )

    def preview(self, context: dict[str, Any]) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        local = self.local.snapshot(context)
        health = self.hosted.health()
        remote_contacted = False
        remote = None
        plan = None
        if health.get("available") and health.get("hosted_verified"):
            try:
                remote = self.hosted.snapshot(context)
                remote_contacted = True
                plan = build_reconciliation_plan(local, remote)
            except HostedPersistenceUnavailable:
                remote = None
        self._audit(
            tenant_id,
            "sync-preview",
            "ready" if remote_contacted else "hosted-unavailable",
            detail={"local_resource_count": local.get("resource_count", 0), "remote_contacted": remote_contacted},
        )
        return public_account_payload(
            {
                "state": "ready" if remote_contacted else "hosted-unavailable",
                "local": local,
                "remote": remote,
                "reconciliation": plan,
                "remote_contacted": remote_contacted,
                "hosted_verified": bool(health.get("hosted_verified") and remote_contacted),
                "hosted_persistence": "verified-test" if remote_contacted else "unavailable",
                "first_sync_consent_required": True,
                "private_fields_excluded": True,
                "provider_call_count": 0,
                "caveat": "No account record is uploaded until explicit first-sync consent is queued.",
            }
        )

    def queue_first_sync(self, context: dict[str, Any], body: Any) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        validated = validate_first_sync_body(body)
        snapshot = self.local.snapshot(context)
        if int(snapshot.get("resource_count") or 0) > MAX_SYNC_RESOURCES:
            raise ValueError("Sync snapshot exceeds the bounded resource count.")
        payload_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload_bytes = len(payload_json.encode("utf-8"))
        if payload_bytes > MAX_SYNC_BYTES:
            raise ValueError("Sync snapshot exceeds the bounded payload size.")
        fingerprint = _hash(snapshot)
        existing = execute_query(
            "SELECT * FROM tenant_sync_mutations WHERE tenant_id=? AND idempotency_key=?",
            (tenant_id, validated["idempotency_key"]),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        if existing:
            if existing.get("snapshot_fingerprint") != fingerprint:
                raise ValueError("Idempotency key was already used for a different sync snapshot.")
            return {**self._public_mutation(existing), "status": "deduped"}
        count = execute_query(
            "SELECT COUNT(*) AS count FROM tenant_sync_mutations WHERE tenant_id=? AND state IN ('pending','retrying','conflict')",
            (tenant_id,),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        if int((count or {}).get("count") or 0) >= MAX_OFFLINE_MUTATIONS:
            raise ValueError("Offline sync queue limit reached.")
        timestamp = _iso()
        mutation_id = new_id("tsm")
        execute_query(
            """
            INSERT INTO tenant_sync_mutations (
                mutation_id, tenant_id, owner_user_id, idempotency_key, operation,
                state, snapshot_json, snapshot_fingerprint, payload_bytes,
                resource_count, attempt_count, consented_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'snapshot-upsert', 'pending', ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                mutation_id,
                tenant_id,
                user_id,
                validated["idempotency_key"],
                payload_json,
                fingerprint,
                payload_bytes,
                int(snapshot.get("resource_count") or 0),
                timestamp,
                timestamp,
                timestamp,
            ),
            db_path=self.db_path,
        )
        self._audit(
            tenant_id,
            "sync-queued",
            "pending",
            mutation_id=mutation_id,
            detail={"payload_bytes": payload_bytes, "resource_count": snapshot.get("resource_count", 0)},
        )
        row = execute_query(
            "SELECT * FROM tenant_sync_mutations WHERE tenant_id=? AND mutation_id=?",
            (tenant_id, mutation_id),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        return self._public_mutation(row or {})

    @staticmethod
    def _public_mutation(row: dict[str, Any]) -> dict[str, Any]:
        return public_account_payload(
            {
                "mutation_id": row.get("mutation_id"),
                "operation": row.get("operation"),
                "status": row.get("state") or "pending",
                "payload_bytes": int(row.get("payload_bytes") or 0),
                "resource_count": int(row.get("resource_count") or 0),
                "attempt_count": int(row.get("attempt_count") or 0),
                "next_retry_at": row.get("next_retry_at"),
                "last_error_code": row.get("last_error_code") or "",
                "remote_revision": row.get("remote_revision") or "",
                "consented_at": row.get("consented_at"),
                "updated_at": row.get("updated_at"),
            }
        )

    def list_queue(self, context: dict[str, Any], *, include_applied: bool = False) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        states = "('pending','retrying','conflict','applied')" if include_applied else "('pending','retrying','conflict')"
        rows = execute_query(
            f"SELECT * FROM tenant_sync_mutations WHERE tenant_id=? AND state IN {states} ORDER BY created_at LIMIT ?",
            (tenant_id, MAX_OFFLINE_MUTATIONS),
            fetch=True,
            db_path=self.db_path,
        )
        return [self._public_mutation(row) for row in rows or []]

    def replay(self, context: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        rows = execute_query(
            """
            SELECT * FROM tenant_sync_mutations
            WHERE tenant_id=? AND state IN ('pending','retrying') AND attempt_count < ?
            ORDER BY created_at LIMIT ?
            """,
            (tenant_id, MAX_RETRY_ATTEMPTS, MAX_REPLAY_BATCH),
            fetch=True,
            db_path=self.db_path,
        )
        if not rows:
            state = self.status(context)
            return {
                "status": "conflict" if state["conflict_count"] else "idle",
                "applied_count": 0,
                "conflict_count": state["conflict_count"],
                "pending_count": state["pending_count"],
                "provider_call_count": 0,
            }
        health = self.hosted.health()
        if not health.get("available") or not health.get("hosted_verified"):
            for row in rows:
                self._mark_retry(tenant_id, row, now=now, error_code="hosted-unavailable")
            state = self.status(context)
            return {
                "status": "offline",
                "applied_count": 0,
                "conflict_count": state["conflict_count"],
                "pending_count": state["pending_count"],
                "provider_call_count": 0,
                "local_research_available": True,
            }
        applied = 0
        conflicts = 0
        for row in rows:
            try:
                result = self.hosted.apply_snapshot(
                    context,
                    json_loads(row.get("snapshot_json"), {}),
                    idempotency_key=str(row.get("idempotency_key") or ""),
                )
            except HostedPersistenceUnavailable:
                self._mark_retry(tenant_id, row, now=now, error_code="hosted-unavailable")
                continue
            result_status = str(result.get("status") or "error")
            if result_status == "conflict":
                conflicts += 1
                execute_query(
                    "UPDATE tenant_sync_mutations SET state='conflict', last_error_code='version-conflict', remote_revision=?, updated_at=? WHERE tenant_id=? AND mutation_id=?",
                    (str(result.get("remote_revision") or "")[:128], _iso(now), tenant_id, row.get("mutation_id")),
                    db_path=self.db_path,
                )
                self._audit(tenant_id, "sync-replay", "conflict", mutation_id=str(row.get("mutation_id") or ""))
            elif result_status in {"applied", "deduped"}:
                applied += 1
                execute_query(
                    "UPDATE tenant_sync_mutations SET state='applied', remote_revision=?, last_error_code='', next_retry_at=NULL, updated_at=? WHERE tenant_id=? AND mutation_id=?",
                    (str(result.get("remote_revision") or "")[:128], _iso(now), tenant_id, row.get("mutation_id")),
                    db_path=self.db_path,
                )
                self._audit(tenant_id, "sync-replay", "applied", mutation_id=str(row.get("mutation_id") or ""))
            else:
                self._mark_retry(tenant_id, row, now=now, error_code="remote-rejected")
        state = self.status(context)
        status = "conflict" if conflicts else ("synced" if applied and not state["pending_count"] else "offline")
        return {
            "status": status,
            "applied_count": applied,
            "conflict_count": state["conflict_count"],
            "pending_count": state["pending_count"],
            "provider_call_count": 0,
            "local_research_available": True,
        }

    def _mark_retry(self, tenant_id: str, row: dict[str, Any], *, now: datetime | None, error_code: str) -> None:
        attempts = int(row.get("attempt_count") or 0) + 1
        delay = min(300, 2 ** min(attempts, 8))
        current = now or datetime.now(timezone.utc)
        next_retry = _iso(current + timedelta(seconds=delay))
        execute_query(
            "UPDATE tenant_sync_mutations SET state='retrying', attempt_count=?, next_retry_at=?, last_error_code=?, updated_at=? WHERE tenant_id=? AND mutation_id=?",
            (attempts, next_retry, error_code[:48], _iso(current), tenant_id, row.get("mutation_id")),
            db_path=self.db_path,
        )
        self._audit(tenant_id, "sync-replay", "retrying", mutation_id=str(row.get("mutation_id") or ""), detail={"attempt_count": attempts, "error_code": error_code})

    def cancel(self, context: dict[str, Any], mutation_id: str) -> bool:
        tenant_id, _ = _require_authenticated(context)
        changed = execute_query(
            "DELETE FROM tenant_sync_mutations WHERE tenant_id=? AND mutation_id=? AND state IN ('pending','retrying','conflict')",
            (tenant_id, str(mutation_id or "")),
            db_path=self.db_path,
        )
        if changed:
            self._audit(tenant_id, "sync-canceled", "canceled", mutation_id=str(mutation_id or ""))
        return bool(changed)

    def status(self, context: dict[str, Any]) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        counts = execute_query(
            """
            SELECT
              SUM(CASE WHEN state IN ('pending','retrying') THEN 1 ELSE 0 END) AS pending_count,
              SUM(CASE WHEN state='conflict' THEN 1 ELSE 0 END) AS conflict_count,
              SUM(CASE WHEN state='applied' THEN 1 ELSE 0 END) AS synced_count,
              MAX(attempt_count) AS max_attempt_count
            FROM tenant_sync_mutations WHERE tenant_id=?
            """,
            (tenant_id,),
            fetch=True,
            one=True,
            db_path=self.db_path,
        ) or {}
        health = self.hosted.health()
        pending = int(counts.get("pending_count") or 0)
        conflicts = int(counts.get("conflict_count") or 0)
        verified = bool(health.get("available") and health.get("hosted_verified"))
        if conflicts:
            state = "conflict"
        elif pending:
            state = "pending" if verified else "hosted-unavailable"
        elif verified and int(counts.get("synced_count") or 0):
            state = "synced"
        else:
            state = "hosted-unavailable"
        return public_account_payload(
            {
                "state": state,
                "local_state": "available",
                "hosted_persistence": "verified-test" if verified else "unavailable",
                "hosted_verified": verified,
                "source_status": str(health.get("source_status") or "unavailable"),
                "pending_count": pending,
                "conflict_count": conflicts,
                "synced_count": int(counts.get("synced_count") or 0),
                "queue_limit": MAX_OFFLINE_MUTATIONS,
                "retry_available": verified and pending > 0,
                "circuit_state": "open" if int(counts.get("max_attempt_count") or 0) >= MAX_RETRY_ATTEMPTS else "closed",
                "provider_call_count": 0,
                "remote_contacted": False,
                "queue": self.list_queue(context),
                "caveat": "Hosted state remains unavailable until live auth, RLS, isolation, recovery, and deletion proof passes.",
            }
        )

    def audit(self, context: dict[str, Any], *, limit: int = 50) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        rows = execute_query(
            "SELECT event_type, status, mutation_id, detail_json, created_at FROM tenant_sync_audit WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, max(1, min(int(limit), 100))),
            fetch=True,
            db_path=self.db_path,
        )
        return [
            public_account_payload(
                {
                    "event_type": row.get("event_type"),
                    "status": row.get("status"),
                    "mutation_id": row.get("mutation_id"),
                    "detail": json_loads(row.get("detail_json"), {}),
                    "created_at": row.get("created_at"),
                }
            )
            for row in rows or []
        ]

