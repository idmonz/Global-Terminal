from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .research_workspace_db import execute_query, json_dumps, json_loads, new_id


IDENTITY_TENANCY_VERSION = "identity_tenancy.v1"
SESSION_COOKIE = "gt_session"
CSRF_COOKIE = "gt_csrf"
MAX_PREFERENCE_BYTES = 16_384
MAX_PREFERENCES_PER_TENANT = 10
_KEY_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_PRIVATE_FIELDS = {
    "access_token",
    "authorization",
    "cookie",
    "csrf_token",
    "db_path",
    "password",
    "private_path",
    "refresh_token",
    "service_role_key",
    "session_token",
    "supabase_anon_key",
    "supabase_publishable_key",
    "supabase_secret_key",
}


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    return current if current.tzinfo else current.replace(tzinfo=timezone.utc)


def _iso(value: datetime | str | None = None) -> str:
    if isinstance(value, str):
        return value
    return _utc(value).replace(microsecond=0).isoformat()


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def anonymous_context(*, state: str = "anonymous-local") -> dict[str, Any]:
    return {
        "state": state,
        "authenticated": False,
        "identity_provider": "none",
        "user_id": None,
        "tenant_id": None,
        "display_name": "Local workspace",
        "role": "local-owner",
        "plan": "local-free",
        "session_expires_at": None,
    }


_LOCAL_IDENTITIES = {
    "analyst-a": {
        "user_id": "usr_local_a_2f41d0",
        "tenant_id": "tnt_local_a_8c31e2",
        "display_name": "Analyst A",
    },
    "analyst-b": {
        "user_id": "usr_local_b_7a28c4",
        "tenant_id": "tnt_local_b_5d90f1",
        "display_name": "Analyst B",
    },
}


def local_test_context(
    alias: str,
    *,
    expires_at: datetime | str | None = None,
) -> dict[str, Any]:
    identity = _LOCAL_IDENTITIES.get(str(alias or "").strip().lower())
    if not identity:
        raise ValueError("Unknown local test identity.")
    return {
        "state": "authenticated-local-test",
        "authenticated": True,
        "identity_provider": "process-local-test",
        **identity,
        "role": "owner",
        "plan": "local-test",
        "session_expires_at": _iso(expires_at) if expires_at else None,
    }


def public_account_payload(value: Any) -> Any:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in _PRIVATE_FIELDS or normalized.endswith("_secret") or normalized.endswith("_token") or normalized.endswith("_path"):
                continue
            output[str(key)] = public_account_payload(item)
        return output
    if isinstance(value, list):
        return [public_account_payload(item) for item in value[:100]]
    if isinstance(value, tuple):
        return [public_account_payload(item) for item in value[:100]]
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def persistence_provider_health() -> dict[str, Any]:
    configured = bool(
        os.getenv("SUPABASE_URL", "").strip()
        and (
            os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
            or os.getenv("SUPABASE_ANON_KEY", "").strip()
        )
    )
    enabled = str(os.getenv("GLOBAL_TERMINAL_HOSTED_AUTH_ENABLED", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return {
        "provider": "supabase",
        "configured": configured,
        "enabled": enabled,
        "contacted": False,
        "successful": False,
        "hosted_verified": False,
        "source_status": "configured-unverified" if configured and enabled else "disabled" if configured else "missing-key",
        "caveat": (
            "Configuration presence is not hosted identity or tenant-isolation proof."
            if configured
            else "Optional Supabase configuration is absent; local mode remains available."
        ),
        "data_gap": "No live Supabase auth, RLS, write, recovery, or isolation test ran.",
    }


def build_account_workspace_contract(
    context: dict[str, Any],
    *,
    provider_calls: int = 0,
    preference: dict[str, Any] | None = None,
    sync_state: str | None = None,
    persistence_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    authenticated = bool(context.get("authenticated"))
    hosted = context.get("identity_provider") == "supabase"
    can_write = bool(authenticated and context.get("role") in {"owner", "member"})
    provider = public_account_payload(persistence_health or persistence_provider_health())
    state = sync_state or ("local-test" if authenticated else "local")
    public_identity = {
        "state": context.get("state"),
        "authenticated": authenticated,
        "identity_provider": context.get("identity_provider"),
        "display_name": context.get("display_name"),
        "role": context.get("role"),
        "plan": context.get("plan"),
        "session_expires_at": context.get("session_expires_at"),
        "account_scope": "server-derived" if authenticated else "local",
    }
    return public_account_payload(
        {
            "identity_tenancy_version": IDENTITY_TENANCY_VERSION,
            "identity": public_identity,
            "workspace": {
                "tenant_scope": "server-derived" if authenticated else "local",
                "role": context.get("role"),
                "read_only": bool(authenticated and not can_write),
                "preference": preference,
                "local_fallback_available": True,
            },
            "persistence": {
                **provider,
                "state": state,
                "local_private_available": True,
                "last_local_save_at": None,
                "last_remote_sync_at": None,
                "conflict": state == "conflict",
            },
            "entitlements": {
                "plan": context.get("plan") or "local-free",
                "account_sync": bool(can_write and (not hosted or provider.get("hosted_verified"))),
                "saved_workspace_limit": MAX_PREFERENCES_PER_TENANT if authenticated else 0,
                "hosted_alert_delivery": False,
                "checkout_enabled": False,
                "billing_active": False,
            },
            "runtime_truth": {
                "process_local_session": bool(authenticated and not hosted),
                "local_test_sign_in_available": local_auth_enabled(),
                "hosted_sign_in_available": bool(
                    persistence_provider_health().get("configured")
                    and persistence_provider_health().get("enabled")
                ),
                "hosted_auth": hosted,
                "hosted_persistence": bool(provider.get("hosted_verified")),
                "account_write": can_write,
                "payment_collection": False,
                "broker_execution": False,
            },
            "summary": {
                "state": context.get("state"),
                "provider_calls": max(0, int(provider_calls)),
                "authenticated": authenticated,
            },
            "caveat": (
                "Hosted identity is session-derived; repository readiness still follows observed read/write and recovery evidence."
                if hosted
                else "Local test identity is process-local and is not production authentication."
            ),
            "not_financial_advice": True,
        }
    )


def validate_return_to(value: Any) -> str:
    candidate = str(value or "/").strip()
    if (
        not candidate.startswith("/")
        or candidate.startswith("//")
        or "\\" in candidate
        or ":" in candidate.split("?", 1)[0]
        or len(candidate) > 512
    ):
        raise ValueError("Unsafe return URL.")
    return candidate


def validate_preference_body(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError("Preference body must be an object.")
    if any(key in body for key in ("tenant_id", "user_id", "owner_user_id")):
        raise ValueError("Tenant and user identity are server-derived.")
    value = body.get("value")
    if not isinstance(value, dict):
        raise ValueError("Preference value must be an object.")
    expected = body.get("expected_version")
    if not isinstance(expected, int) or expected < 0:
        raise ValueError("expected_version must be a non-negative integer.")
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if len(encoded) > MAX_PREFERENCE_BYTES:
        raise ValueError("Preference value exceeds the bounded size.")
    return {"value": public_account_payload(value), "expected_version": expected}


def csrf_matches(expected: str | None, supplied: str | None) -> bool:
    if not expected or not supplied:
        return False
    return hmac.compare_digest(str(expected), str(supplied))


class PreferenceConflict(RuntimeError):
    def __init__(self, current_version: int):
        super().__init__("Preference version conflict.")
        self.current_version = int(current_version)


def _require_authenticated(context: dict[str, Any]) -> tuple[str, str]:
    if not context.get("authenticated"):
        raise PermissionError("Authenticated tenant context required.")
    tenant_id = str(context.get("tenant_id") or "")
    user_id = str(context.get("user_id") or "")
    if not tenant_id or not user_id:
        raise PermissionError("Authenticated tenant context is incomplete.")
    return tenant_id, user_id


def _validate_key(key: str) -> str:
    normalized = str(key or "").strip().lower()
    if not _KEY_RE.fullmatch(normalized):
        raise ValueError("Invalid preference key.")
    return normalized


class SQLiteTenantPreferenceAdapter:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path

    def get(self, context: dict[str, Any], key: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        row = execute_query(
            "SELECT * FROM tenant_workspace_preferences WHERE tenant_id = ? AND preference_key = ?",
            (tenant_id, _validate_key(key)),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        return self._public_row(row)

    def get_by_id(self, context: dict[str, Any], resource_id: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        row = execute_query(
            "SELECT * FROM tenant_workspace_preferences WHERE tenant_id = ? AND resource_id = ?",
            (tenant_id, str(resource_id or "")),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        return self._public_row(row)

    def save(
        self,
        context: dict[str, Any],
        key: str,
        value: dict[str, Any],
        *,
        expected_version: int,
    ) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        normalized = _validate_key(key)
        validated = validate_preference_body(
            {"value": value, "expected_version": expected_version}
        )
        existing = execute_query(
            "SELECT * FROM tenant_workspace_preferences WHERE tenant_id = ? AND preference_key = ?",
            (tenant_id, normalized),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        current_version = int((existing or {}).get("version") or 0)
        if current_version != validated["expected_version"]:
            raise PreferenceConflict(current_version)
        if not existing:
            count = execute_query(
                "SELECT COUNT(*) AS count FROM tenant_workspace_preferences WHERE tenant_id = ?",
                (tenant_id,),
                fetch=True,
                one=True,
                db_path=self.db_path,
            )
            if int((count or {}).get("count") or 0) >= MAX_PREFERENCES_PER_TENANT:
                raise ValueError("Tenant preference limit reached.")
        now = _iso()
        resource_id = str((existing or {}).get("resource_id") or new_id("pref"))
        version = current_version + 1
        if existing:
            execute_query(
                """
                UPDATE tenant_workspace_preferences
                SET owner_user_id = ?, value_json = ?, version = ?, updated_at = ?
                WHERE tenant_id = ? AND resource_id = ?
                """,
                (user_id, json_dumps(validated["value"]), version, now, tenant_id, resource_id),
                db_path=self.db_path,
            )
        else:
            execute_query(
                """
                INSERT INTO tenant_workspace_preferences (
                    resource_id, tenant_id, owner_user_id, preference_key,
                    value_json, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (resource_id, tenant_id, user_id, normalized, json_dumps(validated["value"]), version, now, now),
                db_path=self.db_path,
            )
        return self.get(context, normalized) or {}

    def delete(
        self,
        context: dict[str, Any],
        resource_id: str,
        *,
        expected_version: int,
    ) -> bool:
        tenant_id, _ = _require_authenticated(context)
        existing = self.get_by_id(context, resource_id)
        if not existing:
            return False
        if int(existing["version"]) != int(expected_version):
            raise PreferenceConflict(int(existing["version"]))
        changed = execute_query(
            "DELETE FROM tenant_workspace_preferences WHERE tenant_id = ? AND resource_id = ?",
            (tenant_id, resource_id),
            db_path=self.db_path,
        )
        return bool(changed)

    def export(self, context: dict[str, Any]) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        rows = execute_query(
            "SELECT * FROM tenant_workspace_preferences WHERE tenant_id = ? ORDER BY updated_at DESC LIMIT ?",
            (tenant_id, MAX_PREFERENCES_PER_TENANT),
            fetch=True,
            db_path=self.db_path,
        )
        return {
            "identity_tenancy_version": IDENTITY_TENANCY_VERSION,
            "tenant_id": tenant_id,
            "preferences": [self._public_row(row) for row in (rows or [])],
            "exported_at": _iso(),
            "bounded": True,
        }

    @staticmethod
    def _public_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return public_account_payload(
            {
                "resource_id": row.get("resource_id"),
                "preference_key": row.get("preference_key"),
                "value": json_loads(row.get("value_json"), {}),
                "version": int(row.get("version") or 0),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "source_status": "local-private",
                "persistence_state": "saved-local-test",
            }
        )


class InMemoryTenantPreferenceAdapter:
    def __init__(self):
        self._records: dict[tuple[str, str], dict[str, Any]] = {}

    def get(self, context: dict[str, Any], key: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        value = self._records.get((tenant_id, _validate_key(key)))
        return public_account_payload(dict(value)) if value else None

    def save(self, context: dict[str, Any], key: str, value: dict[str, Any], *, expected_version: int) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        normalized = _validate_key(key)
        current = self._records.get((tenant_id, normalized))
        version = int((current or {}).get("version") or 0)
        if version != expected_version:
            raise PreferenceConflict(version)
        row = {
            "resource_id": (current or {}).get("resource_id") or new_id("pref"),
            "preference_key": normalized,
            "value": validate_preference_body({"value": value, "expected_version": expected_version})["value"],
            "version": version + 1,
            "updated_at": _iso(),
            "source_status": "memory-test",
        }
        self._records[(tenant_id, normalized)] = row
        return public_account_payload(dict(row))


class PersistenceUnavailable(RuntimeError):
    pass


class SupabaseTenantPreferenceAdapter:
    """Optional provider edge; no SDK or hosted-success claim in Phase 6J."""

    def health(self) -> dict[str, Any]:
        return persistence_provider_health()

    def get(self, context: dict[str, Any], key: str) -> dict[str, Any] | None:
        del context, key
        raise PersistenceUnavailable(
            "Supabase persistence is not live-verified in this environment."
        )

    def save(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        del args, kwargs
        raise PersistenceUnavailable(
            "Supabase persistence is not live-verified in this environment."
        )


@dataclass(frozen=True)
class SessionCredentials:
    session_token: str
    csrf_token: str
    expires_at: str


class SessionManager:
    def __init__(self, *, ttl_seconds: int = 3600):
        self.ttl_seconds = max(60, min(int(ttl_seconds), 86_400))
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(str(token).encode("utf-8")).hexdigest()

    def create(
        self,
        alias: str,
        *,
        now: datetime | None = None,
        replace: str | None = None,
    ) -> SessionCredentials:
        current = _utc(now)
        if replace:
            self.revoke(replace)
        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(24)
        expires = current + timedelta(seconds=self.ttl_seconds)
        context = local_test_context(alias, expires_at=expires)
        with self._lock:
            self._sessions[self._hash(session_token)] = {
                "context": context,
                "csrf_hash": self._hash(csrf_token),
                "expires_at": expires,
                "revoked": False,
            }
        return SessionCredentials(session_token, csrf_token, _iso(expires))

    def resolve(self, token: str | None, *, now: datetime | None = None) -> dict[str, Any]:
        if not token:
            return anonymous_context()
        with self._lock:
            record = self._sessions.get(self._hash(token))
            if not record or record.get("revoked"):
                return anonymous_context(state="revoked")
            if _utc(now) >= record["expires_at"]:
                record["revoked"] = True
                return anonymous_context(state="expired")
            return public_account_payload(dict(record["context"]))

    def validate_csrf(self, token: str | None, cookie: str | None, supplied: str | None) -> bool:
        if not token or not csrf_matches(cookie, supplied):
            return False
        with self._lock:
            record = self._sessions.get(self._hash(token))
            return bool(
                record
                and not record.get("revoked")
                and csrf_matches(record.get("csrf_hash"), self._hash(str(supplied)))
            )

    def revoke(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            record = self._sessions.get(self._hash(token))
            if record:
                record["revoked"] = True


class LocalRateLimiter:
    def __init__(self):
        self._events: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else float(now)
        threshold = current - max(1, int(window_seconds))
        with self._lock:
            events = [value for value in self._events.get(key, []) if value > threshold]
            if len(events) >= max(1, int(limit)):
                self._events[key] = events
                return False
            events.append(current)
            self._events[key] = events
            return True


def local_auth_enabled() -> bool:
    return _truthy(os.getenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED"))
