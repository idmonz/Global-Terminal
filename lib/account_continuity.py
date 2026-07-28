from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .identity_tenancy import _require_authenticated
from .research_workspace_db import get_connection, json_dumps, json_loads, new_id
from .supabase_account_runtime import (
    SupabaseAccountDocumentRepository,
    SupabaseRepositoryConflict,
    SupabaseRepositoryUnavailable,
)


ACCOUNT_CONTINUITY_VERSION = "account_continuity.v1"
MAX_ACCOUNT_BUNDLE_BYTES = 512_000
MAX_ACCOUNT_BUNDLE_ROWS = 1_000
MAX_ROWS_PER_TABLE = 250

ACCOUNT_TABLES = (
    "tenant_workspace_preferences",
    "tenant_watchlists",
    "tenant_watchlist_items",
    "tenant_import_receipts",
    "tenant_alert_rules",
    "tenant_inbox_items",
    "tenant_attention_states",
    "tenant_attention_policies",
    "tenant_attention_checkpoints",
    "tenant_attention_audit",
    "tenant_observation_runs",
    "tenant_observation_snapshots",
    "tenant_provider_quota_ledger",
    "tenant_observation_run_audit",
    "tenant_watchlist_alert_rules",
    "tenant_watchlist_alert_evaluations",
    "tenant_watchlist_alert_triggers",
    "tenant_watchlist_alert_audit",
    "tenant_watchlist_alert_worker_state",
    "tenant_hosted_observation_schedules",
    "tenant_hosted_observation_schedule_runs",
    "tenant_hosted_observation_schedule_audit",
)

_AUDIT_TABLES = {
    "tenant_attention_audit",
    "tenant_observation_run_audit",
    "tenant_watchlist_alert_audit",
    "tenant_hosted_observation_schedule_audit",
}
_IDENTITY_FIELDS = {"tenant_id", "owner_user_id", "user_id"}
_PRIVATE_FIELDS = {
    "access_token",
    "authorization",
    "cookie",
    "csrf_token",
    "db_path",
    "password",
    "private_body",
    "private_note",
    "private_path",
    "lease_owner_hash",
    "lease_token_hash",
    "refresh_token",
    "review_notes",
    "service_role_key",
    "session_token",
    "supabase_anon_key",
    "supabase_publishable_key",
    "supabase_secret_key",
    "tenant_id",
    "user_id",
    "owner_user_id",
    "watch_reason",
}


class AccountContinuityValidationError(ValueError):
    pass


class AccountDocumentRepository(Protocol):
    def load(self, context: dict[str, Any]) -> dict[str, Any] | None: ...

    def save(
        self,
        context: dict[str, Any],
        bundle: dict[str, Any],
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def delete(
        self,
        context: dict[str, Any],
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def health(self) -> dict[str, Any]: ...


def _iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_private_key(key: Any) -> bool:
    normalized = str(key or "").strip().lower()
    return (
        normalized in _PRIVATE_FIELDS
        or normalized.startswith("private_")
        or normalized.endswith("_secret")
        or normalized.endswith("_token")
        or normalized.endswith("_path")
    )


def _sanitize(value: Any, *, depth: int = 0) -> Any:
    if depth > 10:
        return "[depth-limited]"
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item, depth=depth + 1)
            for key, item in value.items()
            if not _is_private_key(key)
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item, depth=depth + 1) for item in list(value)[:500]]
    if isinstance(value, str):
        return value[:50_000]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:10_000]


def _sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in row.items():
        if key in _IDENTITY_FIELDS or _is_private_key(key):
            continue
        if key.endswith("_json") and isinstance(value, str):
            parsed = json_loads(value, None)
            output[key] = json_dumps(_sanitize(parsed)) if parsed is not None else "{}"
        else:
            output[key] = _sanitize(value)
    return output


def _encoded_size(value: Any) -> int:
    return len(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    )


def _bundle_tables(value: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, dict):
        raise AccountContinuityValidationError("Account continuity tables must be an object.")
    tables: dict[str, list[dict[str, Any]]] = {}
    for table, raw_rows in value.items():
        if table not in ACCOUNT_TABLES:
            raise AccountContinuityValidationError("Account continuity table is not allowed.")
        if not isinstance(raw_rows, list) or len(raw_rows) > MAX_ROWS_PER_TABLE:
            raise AccountContinuityValidationError("Account continuity table exceeds its row bound.")
        rows: list[dict[str, Any]] = []
        for raw in raw_rows:
            if not isinstance(raw, dict):
                raise AccountContinuityValidationError("Account continuity rows must be objects.")
            if any(field in raw for field in _IDENTITY_FIELDS):
                raise AccountContinuityValidationError("Account identity is server-derived.")
            rows.append(_sanitize_row(raw))
        tables[table] = rows
    if sum(len(rows) for rows in tables.values()) > MAX_ACCOUNT_BUNDLE_ROWS:
        raise AccountContinuityValidationError("Account continuity bundle exceeds its row bound.")
    return tables


def _validate_parent_integrity(tables: dict[str, list[dict[str, Any]]]) -> None:
    watchlists = {str(row.get("resource_id") or "") for row in tables.get("tenant_watchlists", [])}
    runs = {str(row.get("run_id") or "") for row in tables.get("tenant_observation_runs", [])}
    snapshots = {str(row.get("snapshot_id") or "") for row in tables.get("tenant_observation_snapshots", [])}
    rules = {str(row.get("resource_id") or "") for row in tables.get("tenant_watchlist_alert_rules", [])}
    evaluations = {str(row.get("run_id") or "") for row in tables.get("tenant_watchlist_alert_evaluations", [])}
    schedules = {str(row.get("schedule_id") or "") for row in tables.get("tenant_hosted_observation_schedules", [])}
    scheduler_runs = {str(row.get("scheduler_run_id") or "") for row in tables.get("tenant_hosted_observation_schedule_runs", [])}

    for table, parent_key in (
        ("tenant_watchlist_items", "watchlist_resource_id"),
        ("tenant_alert_rules", "watchlist_resource_id"),
        ("tenant_inbox_items", "watchlist_resource_id"),
        ("tenant_observation_runs", "watchlist_resource_id"),
        ("tenant_watchlist_alert_rules", "watchlist_resource_id"),
    ):
        for row in tables.get(table, []):
            if str(row.get(parent_key) or "") not in watchlists:
                raise AccountContinuityValidationError("Account continuity watchlist parent is missing.")
    for table in ("tenant_observation_snapshots", "tenant_provider_quota_ledger", "tenant_observation_run_audit"):
        for row in tables.get(table, []):
            if str(row.get("run_id") or "") not in runs:
                raise AccountContinuityValidationError("Account continuity observation parent is missing.")
    for row in tables.get("tenant_watchlist_alert_triggers", []):
        if (
            str(row.get("rule_resource_id") or "") not in rules
            or str(row.get("evaluation_run_id") or "") not in evaluations
            or str(row.get("snapshot_id") or "") not in snapshots
        ):
            raise AccountContinuityValidationError("Account continuity alert parent is missing.")
    for row in tables.get("tenant_hosted_observation_schedules", []):
        if (
            str(row.get("watchlist_resource_id") or "") not in watchlists
            or str(row.get("alert_rule_resource_id") or "") not in rules
        ):
            raise AccountContinuityValidationError("Account continuity hosted schedule parent is missing.")
    for row in tables.get("tenant_hosted_observation_schedule_runs", []):
        if str(row.get("schedule_id") or "") not in schedules:
            raise AccountContinuityValidationError("Account continuity hosted scheduler run parent is missing.")
    for row in tables.get("tenant_hosted_observation_schedule_audit", []):
        run_id = str(row.get("scheduler_run_id") or "")
        if str(row.get("schedule_id") or "") not in schedules or (run_id and run_id not in scheduler_runs):
            raise AccountContinuityValidationError("Account continuity hosted scheduler audit parent is missing.")


def _public_bundle(tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    canonical_tables = {
        table: sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, default=str))
        for table, rows in sorted(tables.items())
        if rows
    }
    output = {
        "account_continuity_version": ACCOUNT_CONTINUITY_VERSION,
        "tables": canonical_tables,
        "table_count": len(canonical_tables),
        "row_count": sum(len(rows) for rows in canonical_tables.values()),
        "captured_at": _iso(),
        "bounded": True,
        "provider_call_count": 0,
        "excluded_fields": ["credentials", "identity", "local-paths", "private-notes"],
    }
    output["fingerprint"] = _fingerprint(canonical_tables)
    output["payload_bytes"] = _encoded_size(output)
    if output["payload_bytes"] > MAX_ACCOUNT_BUNDLE_BYTES:
        raise AccountContinuityValidationError("Account continuity bundle exceeds its byte bound.")
    return output


class AccountBundleStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path

    def capture(self, context: dict[str, Any]) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        tables: dict[str, list[dict[str, Any]]] = {}
        with get_connection(self.db_path) as conn:
            for table in ACCOUNT_TABLES:
                rows = conn.execute(
                    f"SELECT * FROM {table} WHERE tenant_id=? ORDER BY rowid LIMIT ?",
                    (tenant_id, MAX_ROWS_PER_TABLE),
                ).fetchall()
                if rows:
                    tables[table] = [_sanitize_row(dict(row)) for row in rows]
        _validate_parent_integrity(tables)
        return _public_bundle(tables)

    def restore(
        self,
        context: dict[str, Any],
        bundle: dict[str, Any],
        *,
        prefer_remote: bool = False,
    ) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        if not isinstance(bundle, dict) or bundle.get("account_continuity_version") != ACCOUNT_CONTINUITY_VERSION:
            raise AccountContinuityValidationError("Unsupported account continuity version.")
        if any(field in bundle for field in _IDENTITY_FIELDS):
            raise AccountContinuityValidationError("Account identity is server-derived.")
        tables = _bundle_tables(bundle.get("tables") or {})
        _validate_parent_integrity(tables)
        expected_fingerprint = str(bundle.get("fingerprint") or "")
        actual_fingerprint = _fingerprint(
            {
                table: sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, default=str))
                for table, rows in sorted(tables.items())
                if rows
            }
        )
        if expected_fingerprint and not hmac_compare(expected_fingerprint, actual_fingerprint):
            raise AccountContinuityValidationError("Account continuity fingerprint mismatch.")
        if _encoded_size(bundle) > MAX_ACCOUNT_BUNDLE_BYTES:
            raise AccountContinuityValidationError("Account continuity bundle exceeds its byte bound.")

        inserted = 0
        updated = 0
        unchanged = 0
        conflicts: list[dict[str, Any]] = []
        with get_connection(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            if prefer_remote:
                for table in reversed(ACCOUNT_TABLES):
                    if table not in _AUDIT_TABLES:
                        conn.execute(f"DELETE FROM {table} WHERE tenant_id=?", (tenant_id,))
            for table in ACCOUNT_TABLES:
                rows = tables.get(table, [])
                if not rows:
                    continue
                info = conn.execute(f"PRAGMA table_info({table})").fetchall()
                columns = {str(row[1]): row for row in info}
                primary = next((str(row[1]) for row in info if int(row[5]) > 0), "")
                if not primary:
                    raise AccountContinuityValidationError("Account continuity table has no stable primary key.")
                for raw in rows:
                    if any(key not in columns for key in raw):
                        raise AccountContinuityValidationError("Account continuity row contains an unknown column.")
                    row = dict(raw)
                    if "tenant_id" in columns:
                        row["tenant_id"] = tenant_id
                    if "owner_user_id" in columns:
                        row["owner_user_id"] = user_id
                    identity = row.get(primary)
                    if identity in (None, ""):
                        raise AccountContinuityValidationError("Account continuity row has no stable identity.")
                    existing_raw = conn.execute(
                        f"SELECT * FROM {table} WHERE {primary}=? AND tenant_id=?",
                        (identity, tenant_id),
                    ).fetchone()
                    if table in _AUDIT_TABLES:
                        if existing_raw:
                            unchanged += 1
                            continue
                        _insert_row(conn, table, row)
                        inserted += 1
                        continue
                    if not existing_raw:
                        _insert_row(conn, table, row)
                        inserted += 1
                        continue
                    existing = dict(existing_raw)
                    remote_version = int(row.get("version") or 0)
                    local_version = int(existing.get("version") or 0)
                    comparable_existing = {key: existing.get(key) for key in row}
                    if remote_version < local_version or (
                        remote_version == local_version
                        and _fingerprint(comparable_existing) != _fingerprint(row)
                    ):
                        conflicts.append(
                            {
                                "table": table,
                                "resource_id": str(identity),
                                "local_version": local_version,
                                "remote_version": remote_version,
                            }
                        )
                        continue
                    if comparable_existing == row:
                        unchanged += 1
                        continue
                    assignments = [key for key in row if key != primary]
                    conn.execute(
                        f"UPDATE {table} SET {', '.join(f'{key}=?' for key in assignments)} WHERE {primary}=? AND tenant_id=?",
                        (*[row[key] for key in assignments], identity, tenant_id),
                    )
                    updated += 1
            conn.commit()
        return {
            "status": "conflict" if conflicts else "restored",
            "inserted_count": inserted,
            "updated_count": updated,
            "unchanged_count": unchanged,
            "conflict_count": len(conflicts),
            "conflicts": conflicts[:50],
            "fingerprint": actual_fingerprint,
            "provider_call_count": 0,
        }


def _insert_row(conn: Any, table: str, row: dict[str, Any]) -> None:
    keys = list(row)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})",
        tuple(row[key] for key in keys),
    )


def hmac_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(str(left), str(right))


def account_continuity_enabled() -> bool:
    return str(os.getenv("GLOBAL_TERMINAL_ACCOUNT_CONTINUITY_ENABLED", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class AccountContinuityCoordinator:
    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        repository: AccountDocumentRepository | None = None,
        enabled: bool | None = None,
    ):
        self.db_path = db_path
        self.bundle_store = AccountBundleStore(db_path)
        self.repository = repository or SupabaseAccountDocumentRepository()
        self.enabled = account_continuity_enabled() if enabled is None else bool(enabled)

    def _state_row(self, tenant_id: str) -> dict[str, Any] | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tenant_account_continuity_state WHERE tenant_id=?",
                (tenant_id,),
            ).fetchone()
        return dict(row) if row else None

    def _set_state(
        self,
        context: dict[str, Any],
        state: str,
        *,
        remote_version: int | None = None,
        local_fingerprint: str | None = None,
        remote_fingerprint: str | None = None,
        restore: bool = False,
        synced: bool = False,
        recovered: bool = False,
        error_code: str = "",
    ) -> None:
        tenant_id, user_id = _require_authenticated(context)
        now = _iso()
        current = self._state_row(tenant_id) or {}
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tenant_account_continuity_state (
                  tenant_id, owner_user_id, state, remote_version,
                  local_fingerprint, remote_fingerprint, last_restore_at,
                  last_sync_at, last_recovery_at, last_failure_at,
                  last_error_code, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id) DO UPDATE SET
                  owner_user_id=excluded.owner_user_id,
                  state=excluded.state,
                  remote_version=excluded.remote_version,
                  local_fingerprint=excluded.local_fingerprint,
                  remote_fingerprint=excluded.remote_fingerprint,
                  last_restore_at=excluded.last_restore_at,
                  last_sync_at=excluded.last_sync_at,
                  last_recovery_at=excluded.last_recovery_at,
                  last_failure_at=excluded.last_failure_at,
                  last_error_code=excluded.last_error_code,
                  updated_at=excluded.updated_at
                """,
                (
                    tenant_id,
                    user_id,
                    state,
                    int(remote_version if remote_version is not None else current.get("remote_version") or 0),
                    str(local_fingerprint if local_fingerprint is not None else current.get("local_fingerprint") or ""),
                    str(remote_fingerprint if remote_fingerprint is not None else current.get("remote_fingerprint") or ""),
                    now if restore else current.get("last_restore_at"),
                    now if synced else current.get("last_sync_at"),
                    now if recovered else current.get("last_recovery_at"),
                    now if error_code else current.get("last_failure_at"),
                    str(error_code or ""),
                    now,
                ),
            )
            conn.commit()

    def _audit(
        self,
        context: dict[str, Any],
        event_type: str,
        status: str,
        *,
        mutation_id: str = "",
        fingerprint: str = "",
    ) -> None:
        tenant_id, _ = _require_authenticated(context)
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO tenant_account_continuity_audit (event_id, tenant_id, event_type, status, mutation_id, fingerprint, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_id("aca"), tenant_id, event_type[:64], status[:32], mutation_id[:80], fingerprint[:64], _iso()),
            )
            conn.commit()

    def _queue(
        self,
        context: dict[str, Any],
        bundle: dict[str, Any],
        *,
        expected_version: int,
        idempotency_key: str,
        state: str,
        error_code: str,
    ) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        now = _iso()
        with get_connection(self.db_path) as conn:
            existing = conn.execute(
                "SELECT * FROM tenant_account_continuity_queue WHERE tenant_id=? AND idempotency_key=?",
                (tenant_id, idempotency_key),
            ).fetchone()
            if existing:
                row = dict(existing)
                if str(row.get("bundle_fingerprint")) != str(bundle.get("fingerprint")):
                    raise AccountContinuityValidationError("Account continuity idempotency key was reused.")
                return self._public_queue(row, deduped=True)
            mutation_id = new_id("acm")
            conn.execute(
                """
                INSERT INTO tenant_account_continuity_queue (
                  mutation_id, tenant_id, owner_user_id, idempotency_key,
                  operation, state, bundle_json, bundle_fingerprint,
                  expected_version, attempt_count, last_error_code,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'apply', ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    mutation_id,
                    tenant_id,
                    user_id,
                    idempotency_key,
                    state,
                    json_dumps(bundle),
                    bundle["fingerprint"],
                    max(0, int(expected_version)),
                    error_code,
                    now,
                    now,
                ),
            )
            conn.commit()
        self._audit(
            context,
            "continuity-queued",
            state,
            mutation_id=mutation_id,
            fingerprint=str(bundle.get("fingerprint") or ""),
        )
        return {
            "mutation_id": mutation_id,
            "status": state,
            "deduped": False,
            "provider_call_count": 0,
        }

    @staticmethod
    def _public_queue(row: dict[str, Any], *, deduped: bool = False) -> dict[str, Any]:
        return {
            "mutation_id": row.get("mutation_id"),
            "status": row.get("state"),
            "expected_version": int(row.get("expected_version") or 0),
            "attempt_count": int(row.get("attempt_count") or 0),
            "last_error_code": row.get("last_error_code"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "deduped": deduped,
            "provider_call_count": 0,
        }

    def restore(self, context: dict[str, Any], *, prefer_remote: bool = False) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        local = self.bundle_store.capture(context)
        if not self.enabled or context.get("identity_provider") != "supabase":
            self._set_state(context, "local-only", local_fingerprint=local["fingerprint"])
            return {
                "status": "local-only",
                "local": {"row_count": local["row_count"], "fingerprint": local["fingerprint"]},
                "remote_contacted": False,
                "provider_call_count": 0,
            }
        try:
            remote = self.repository.load(context)
        except (SupabaseRepositoryUnavailable, SupabaseAccountErrorCompat):
            self._set_state(
                context,
                "offline-read-only",
                local_fingerprint=local["fingerprint"],
                error_code="hosted-repository-unavailable",
            )
            self._audit(context, "continuity-restore", "offline", fingerprint=local["fingerprint"])
            return {
                "status": "offline-read-only",
                "local": {"row_count": local["row_count"], "fingerprint": local["fingerprint"]},
                "remote_contacted": True,
                "provider_call_count": 0,
            }
        if not remote:
            self._set_state(
                context,
                "hosted-ready",
                remote_version=0,
                local_fingerprint=local["fingerprint"],
                remote_fingerprint="",
                restore=True,
            )
            self._audit(context, "continuity-restore", "remote-empty", fingerprint=local["fingerprint"])
            return {
                "status": "hosted-ready",
                "remote_version": 0,
                "restored_count": 0,
                "remote_contacted": True,
                "provider_call_count": 0,
            }
        remote_bundle = remote.get("payload") if isinstance(remote.get("payload"), dict) else {}
        remote_fingerprint = str(remote.get("fingerprint") or remote_bundle.get("fingerprint") or "")
        state = self._state_row(tenant_id) or {}
        safe_to_restore = (
            prefer_remote
            or local["row_count"] == 0
            or local["fingerprint"] == remote_fingerprint
            or local["fingerprint"] == str(state.get("remote_fingerprint") or "")
        )
        if not safe_to_restore:
            self._set_state(
                context,
                "conflict",
                remote_version=int(remote.get("version") or 0),
                local_fingerprint=local["fingerprint"],
                remote_fingerprint=remote_fingerprint,
                restore=True,
                error_code="local-remote-diverged",
            )
            self._audit(context, "continuity-restore", "conflict", fingerprint=local["fingerprint"])
            return {
                "status": "conflict",
                "local_fingerprint": local["fingerprint"],
                "remote_fingerprint": remote_fingerprint,
                "remote_version": int(remote.get("version") or 0),
                "remote_contacted": True,
                "provider_call_count": 0,
            }
        restored = self.bundle_store.restore(context, remote_bundle, prefer_remote=prefer_remote)
        refreshed = self.bundle_store.capture(context)
        status = "hosted-ready" if restored["status"] == "restored" else "conflict"
        self._set_state(
            context,
            status,
            remote_version=int(remote.get("version") or 0),
            local_fingerprint=refreshed["fingerprint"],
            remote_fingerprint=remote_fingerprint,
            restore=True,
            recovered=bool(prefer_remote),
            error_code="" if status == "hosted-ready" else "local-restore-conflict",
        )
        self._audit(context, "continuity-restore", status, fingerprint=refreshed["fingerprint"])
        return {
            **restored,
            "status": status,
            "remote_version": int(remote.get("version") or 0),
            "remote_contacted": True,
            "provider_call_count": 0,
        }

    def sync(self, context: dict[str, Any], *, idempotency_key: str) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        bundle = self.bundle_store.capture(context)
        state = self._state_row(tenant_id) or {}
        expected_version = int(state.get("remote_version") or 0)
        if not self.enabled or context.get("identity_provider") != "supabase":
            return {
                "status": "local-only",
                "remote_contacted": False,
                "local_fingerprint": bundle["fingerprint"],
                "provider_call_count": 0,
            }
        try:
            result = self.repository.save(
                context,
                bundle,
                expected_version=expected_version,
                idempotency_key=idempotency_key,
            )
        except SupabaseRepositoryConflict as exc:
            queued = self._queue(
                context,
                bundle,
                expected_version=exc.current_version,
                idempotency_key=idempotency_key,
                state="conflict",
                error_code="remote-version-conflict",
            )
            self._set_state(
                context,
                "conflict",
                remote_version=exc.current_version,
                local_fingerprint=bundle["fingerprint"],
                error_code="remote-version-conflict",
            )
            return {**queued, "current_version": exc.current_version, "remote_contacted": True}
        except (SupabaseRepositoryUnavailable, SupabaseAccountErrorCompat):
            queued = self._queue(
                context,
                bundle,
                expected_version=expected_version,
                idempotency_key=idempotency_key,
                state="pending",
                error_code="hosted-repository-unavailable",
            )
            self._set_state(
                context,
                "offline-read-only",
                local_fingerprint=bundle["fingerprint"],
                error_code="hosted-repository-unavailable",
            )
            return {**queued, "remote_contacted": True}
        remote_version = int(result.get("version") or expected_version)
        self._set_state(
            context,
            "hosted-ready",
            remote_version=remote_version,
            local_fingerprint=bundle["fingerprint"],
            remote_fingerprint=str(result.get("fingerprint") or bundle["fingerprint"]),
            synced=True,
        )
        self._audit(context, "continuity-sync", str(result.get("status") or "applied"), fingerprint=bundle["fingerprint"])
        return {
            "status": str(result.get("status") or "applied"),
            "remote_version": remote_version,
            "remote_contacted": True,
            "local_fingerprint": bundle["fingerprint"],
            "provider_call_count": 0,
        }

    def replay(self, context: dict[str, Any], *, limit: int = 10) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        state = self._state_row(tenant_id) or {}
        current_version = int(state.get("remote_version") or 0)
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM tenant_account_continuity_queue WHERE tenant_id=? AND state='pending' ORDER BY created_at LIMIT ?",
                (tenant_id, max(1, min(int(limit), 10))),
            ).fetchall()
        applied = 0
        for raw in rows:
            row = dict(raw)
            bundle = json_loads(row.get("bundle_json"), {})
            expected_version = current_version if applied else int(row.get("expected_version") or 0)
            try:
                result = self.repository.save(
                    context,
                    bundle,
                    expected_version=expected_version,
                    idempotency_key=str(row.get("idempotency_key") or ""),
                )
            except SupabaseRepositoryConflict as exc:
                self._update_queue(row, state="conflict", error_code="remote-version-conflict", expected_version=exc.current_version)
                self._set_state(context, "conflict", remote_version=exc.current_version, error_code="remote-version-conflict")
                continue
            except (SupabaseRepositoryUnavailable, SupabaseAccountErrorCompat):
                self._update_queue(row, state="pending", error_code="hosted-repository-unavailable")
                self._set_state(context, "offline-read-only", error_code="hosted-repository-unavailable")
                break
            self._update_queue(row, state="applied", error_code="")
            current_version = int(result.get("version") or expected_version)
            self._set_state(
                context,
                "hosted-ready",
                remote_version=current_version,
                local_fingerprint=str(bundle.get("fingerprint") or ""),
                remote_fingerprint=str(result.get("fingerprint") or bundle.get("fingerprint") or ""),
                synced=True,
                recovered=True,
            )
            applied += 1
        return {
            "status": "recovered" if applied else "no-due-work" if not rows else self.status(context)["state"],
            "applied_count": applied,
            "pending_count": len(self._queue_rows(tenant_id, "pending")),
            "conflict_count": len(self._queue_rows(tenant_id, "conflict")),
            "provider_call_count": 0,
        }

    def _update_queue(
        self,
        row: dict[str, Any],
        *,
        state: str,
        error_code: str,
        expected_version: int | None = None,
    ) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE tenant_account_continuity_queue SET state=?, expected_version=?, attempt_count=attempt_count+1, last_error_code=?, updated_at=? WHERE mutation_id=? AND tenant_id=?",
                (
                    state,
                    int(expected_version if expected_version is not None else row.get("expected_version") or 0),
                    error_code,
                    _iso(),
                    row["mutation_id"],
                    row["tenant_id"],
                ),
            )
            conn.commit()

    def _queue_rows(self, tenant_id: str, state: str) -> list[dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM tenant_account_continuity_queue WHERE tenant_id=? AND state=? ORDER BY created_at LIMIT 100",
                (tenant_id, state),
            ).fetchall()
        return [dict(row) for row in rows]

    def resolve_conflict(
        self,
        context: dict[str, Any],
        *,
        strategy: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        normalized = str(strategy or "").strip().lower()
        if normalized == "use-hosted":
            result = self.restore(context, prefer_remote=True)
            if result.get("status") != "hosted-ready":
                return result
            self._close_conflicts(context, "discarded-local")
            return {**result, "resolution": "use-hosted"}
        if normalized == "keep-local":
            remote = self.repository.load(context)
            tenant_id, _ = _require_authenticated(context)
            current_version = int((remote or {}).get("version") or 0)
            current_fingerprint = str((remote or {}).get("fingerprint") or "")
            state = self._state_row(tenant_id) or {}
            self._set_state(
                context,
                "recovering",
                remote_version=current_version,
                remote_fingerprint=current_fingerprint or str(state.get("remote_fingerprint") or ""),
            )
            result = self.sync(context, idempotency_key=idempotency_key)
            if result.get("status") in {"applied", "deduped"}:
                self._close_conflicts(context, "applied-local")
                return {**result, "resolution": "keep-local"}
            return result
        raise AccountContinuityValidationError("Conflict strategy must be use-hosted or keep-local.")

    def _close_conflicts(self, context: dict[str, Any], status: str) -> None:
        tenant_id, _ = _require_authenticated(context)
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE tenant_account_continuity_queue SET state=?, updated_at=? WHERE tenant_id=? AND state='conflict'",
                (status, _iso(), tenant_id),
            )
            conn.commit()

    def status(self, context: dict[str, Any]) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        row = self._state_row(tenant_id) or {}
        pending = self._queue_rows(tenant_id, "pending")
        conflicts = self._queue_rows(tenant_id, "conflict")
        health = self.repository.health()
        state = str(row.get("state") or ("hosted-unavailable" if self.enabled else "local-only"))
        return {
            "account_continuity_version": ACCOUNT_CONTINUITY_VERSION,
            "state": state,
            "enabled": self.enabled,
            "remote_version": int(row.get("remote_version") or 0),
            "pending_count": len(pending),
            "conflict_count": len(conflicts),
            "last_restore_at": row.get("last_restore_at"),
            "last_sync_at": row.get("last_sync_at"),
            "last_recovery_at": row.get("last_recovery_at"),
            "last_failure_at": row.get("last_failure_at"),
            "last_error_code": row.get("last_error_code"),
            "repository": health,
            "provider_call_count": 0,
            "caveat": "Account persistence never spends market-provider quota.",
        }

    def export(self, context: dict[str, Any]) -> dict[str, Any]:
        bundle = self.bundle_store.capture(context)
        return {
            **bundle,
            "export_scope": "current-session-tenant",
            "hosted_state": self.status(context)["state"],
            "caveat": "Export excludes credentials, identity fields, local paths, and private notes.",
        }

    def import_backup(
        self,
        context: dict[str, Any],
        bundle: dict[str, Any],
        *,
        strategy: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        normalized = str(strategy or "merge").strip().lower()
        if normalized not in {"merge", "replace"}:
            raise AccountContinuityValidationError("Backup strategy must be merge or replace.")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{7,127}", str(idempotency_key or "")):
            raise AccountContinuityValidationError("Invalid backup idempotency key.")
        restored = self.bundle_store.restore(
            context,
            bundle,
            prefer_remote=normalized == "replace",
        )
        if restored.get("status") == "conflict":
            self._set_state(context, "conflict", error_code="backup-restore-conflict")
            self._audit(
                context,
                "continuity-backup-import",
                "conflict",
                fingerprint=str(restored.get("fingerprint") or ""),
            )
            return {
                "status": "conflict",
                "strategy": normalized,
                "restore": restored,
                "remote_contacted": False,
                "provider_call_count": 0,
            }
        persistence = self.sync(context, idempotency_key=idempotency_key)
        status = str(persistence.get("status") or "restored-local")
        self._audit(
            context,
            "continuity-backup-import",
            status,
            fingerprint=str(restored.get("fingerprint") or ""),
        )
        return {
            "status": status,
            "strategy": normalized,
            "restore": restored,
            "persistence": persistence,
            "provider_call_count": 0,
        }

    def delete_hosted(self, context: dict[str, Any], *, idempotency_key: str) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        state = self._state_row(tenant_id) or {}
        if not self.enabled or context.get("identity_provider") != "supabase":
            return {"status": "local-only", "remote_contacted": False, "provider_call_count": 0}
        try:
            result = self.repository.delete(
                context,
                expected_version=int(state.get("remote_version") or 0),
                idempotency_key=idempotency_key,
            )
        except SupabaseRepositoryConflict as exc:
            self._set_state(
                context,
                "conflict",
                remote_version=exc.current_version,
                error_code="remote-version-conflict",
            )
            return {
                "status": "conflict",
                "current_version": exc.current_version,
                "remote_contacted": True,
                "provider_call_count": 0,
            }
        except (SupabaseRepositoryUnavailable, SupabaseAccountErrorCompat):
            self._set_state(context, "offline-read-only", error_code="hosted-repository-unavailable")
            return {
                "status": "offline-read-only",
                "remote_contacted": True,
                "provider_call_count": 0,
            }
        self._set_state(
            context,
            "hosted-deleted-local-retained",
            remote_version=int(result.get("version") or 0),
            remote_fingerprint="",
            synced=True,
        )
        self._audit(context, "continuity-delete", str(result.get("status") or "deleted"))
        return {
            **result,
            "local_retained": True,
            "remote_contacted": True,
            "provider_call_count": 0,
        }


# A narrow compatibility tuple keeps fake repositories free to raise the public
# runtime base error without coupling this module to transport internals.
try:
    from .supabase_account_runtime import SupabaseAccountError as SupabaseAccountErrorCompat
except Exception:  # pragma: no cover
    SupabaseAccountErrorCompat = SupabaseRepositoryUnavailable
