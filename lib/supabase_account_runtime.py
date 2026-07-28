from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

import requests

from .identity_tenancy import SessionCredentials, anonymous_context


SUPABASE_ACCOUNT_RUNTIME_VERSION = "supabase_account_runtime.v1"
ACCOUNT_DOCUMENT_KEY = "research-continuity"
_EMAIL_RE = re.compile(r"^[^\s@]{1,128}@[^\s@]{1,190}$")
_IDEMPOTENCY_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{7,127}$")
_FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")
_MAX_AUTH_PASSWORD_LENGTH = 1024


class SupabaseAccountError(RuntimeError):
    """Public-safe base error for the optional hosted account boundary."""


class SupabaseAuthenticationError(SupabaseAccountError):
    def __init__(self, message: str, *, stage: str = "auth-unverified"):
        super().__init__(message)
        normalized = re.sub(r"[^a-z0-9-]+", "-", str(stage).strip().lower()).strip("-")
        self.stage = normalized[:64] or "auth-unverified"


class SupabaseRepositoryUnavailable(SupabaseAccountError):
    pass


class SupabaseRepositoryConflict(SupabaseAccountError):
    def __init__(self, current_version: int):
        super().__init__("Hosted account version conflict.")
        self.current_version = max(0, int(current_version))


def hosted_auth_enabled(config: "SupabaseAccountConfig | None" = None) -> bool:
    enabled = str(os.getenv("GLOBAL_TERMINAL_HOSTED_AUTH_ENABLED", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    candidate = config or SupabaseAccountConfig.from_env()
    return bool(enabled and candidate.configured)


@dataclass(frozen=True)
class SupabaseAccountConfig:
    url: str
    publishable_key: str = field(repr=False)
    timeout_seconds: float = 8.0

    def __post_init__(self) -> None:
        normalized_url = str(self.url or "").strip().rstrip("/")
        object.__setattr__(self, "url", normalized_url)
        object.__setattr__(self, "publishable_key", str(self.publishable_key or "").strip())
        object.__setattr__(self, "timeout_seconds", max(1.0, min(float(self.timeout_seconds), 30.0)))

    @property
    def configured(self) -> bool:
        return bool(self.url and self.publishable_key and self.url.startswith("https://"))

    @classmethod
    def from_env(cls) -> "SupabaseAccountConfig":
        key = (
            os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
            or os.getenv("SUPABASE_ANON_KEY", "").strip()
        )
        timeout = float(os.getenv("GLOBAL_TERMINAL_SUPABASE_TIMEOUT_SECONDS", "8") or 8)
        return cls(os.getenv("SUPABASE_URL", ""), key, timeout)


class HttpTransport(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> Any: ...


class RequestsTransport:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        return self.session.request(method, url, **kwargs)


def _json_response(response: Any) -> Any:
    try:
        return response.json()
    except Exception as exc:
        raise SupabaseRepositoryUnavailable("Hosted account provider returned an invalid response.") from exc


def _safe_clock(timestamp: float | None = None) -> str:
    value = timestamp if timestamp is not None else time.time()
    return datetime.fromtimestamp(value, tz=timezone.utc).replace(microsecond=0).isoformat()


class SupabaseRepositoryHealth:
    def __init__(self, config: SupabaseAccountConfig):
        self.config = config
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {
            "contacted": False,
            "authenticated": False,
            "rls_verified": False,
            "read_successful": False,
            "write_successful": False,
            "recovery_successful": False,
            "last_contact_at": None,
            "last_auth_at": None,
            "last_read_at": None,
            "last_write_at": None,
            "last_conflict_at": None,
            "last_failure_at": None,
            "last_recovery_at": None,
            "read_count": 0,
            "write_count": 0,
            "conflict_count": 0,
            "failure_count": 0,
            "latency_samples_ms": [],
        }

    def record(
        self,
        operation: str,
        *,
        success: bool,
        latency_ms: float | None = None,
        authenticated: bool = False,
        conflict: bool = False,
        recovery: bool = False,
    ) -> None:
        current = _safe_clock()
        with self._lock:
            self._state["contacted"] = True
            self._state["last_contact_at"] = current
            if latency_ms is not None:
                samples = list(self._state["latency_samples_ms"])
                samples.append(round(max(0.0, float(latency_ms)), 3))
                self._state["latency_samples_ms"] = samples[-100:]
            if authenticated:
                self._state["authenticated"] = True
                self._state["last_auth_at"] = current
            if operation == "read":
                self._state["read_count"] += 1
                if success:
                    self._state["read_successful"] = True
                    self._state["rls_verified"] = authenticated
                    self._state["last_read_at"] = current
            if operation == "write":
                self._state["write_count"] += 1
                if success:
                    self._state["write_successful"] = True
                    self._state["rls_verified"] = authenticated
                    self._state["last_write_at"] = current
            if conflict:
                self._state["conflict_count"] += 1
                self._state["last_conflict_at"] = current
            if recovery and success:
                self._state["recovery_successful"] = True
                self._state["last_recovery_at"] = current
            if not success and not conflict:
                self._state["failure_count"] += 1
                self._state["last_failure_at"] = current

    def public_snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = {**self._state, "latency_samples_ms": list(self._state["latency_samples_ms"])}
        samples = sorted(float(value) for value in state.pop("latency_samples_ms"))
        p50 = samples[(len(samples) - 1) // 2] if samples else None
        p95 = samples[min(len(samples) - 1, int(len(samples) * 0.95))] if samples else None
        hosted_verified = bool(
            state["authenticated"]
            and state["rls_verified"]
            and state["read_successful"]
            and state["write_successful"]
        )
        if hosted_verified:
            source_status = "hosted-ready"
        elif state["last_failure_at"]:
            source_status = "unavailable"
        elif self.config.configured:
            source_status = "configured-unverified"
        else:
            source_status = "missing-key"
        return {
            "provider": "supabase",
            "adapter": "supabase-account-document",
            "configured": self.config.configured,
            **state,
            "hosted": True,
            "hosted_verified": hosted_verified,
            "source_status": source_status,
            "latency_ms": {"sample_count": len(samples), "p50": p50, "p95": p95},
            "provider_call_count": 0,
            "caveat": (
                "Hosted-ready requires a verified user session plus successful RLS-bound read and write."
            ),
        }


class SupabaseAuthClient:
    def __init__(
        self,
        config: SupabaseAccountConfig | None = None,
        *,
        transport: HttpTransport | None = None,
        health: SupabaseRepositoryHealth | None = None,
    ):
        self.config = config or SupabaseAccountConfig.from_env()
        self.transport = transport or RequestsTransport()
        self.health = health or SupabaseRepositoryHealth(self.config)

    def _headers(self, access_token: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.config.publishable_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    def _request(self, method: str, path: str, *, operation: str = "auth", **kwargs: Any) -> Any:
        if not self.config.configured:
            raise SupabaseRepositoryUnavailable("Hosted account provider is not configured.")
        started = time.perf_counter()
        try:
            response = self.transport.request(
                method,
                f"{self.config.url}{path}",
                timeout=self.config.timeout_seconds,
                **kwargs,
            )
        except Exception as exc:
            self.health.record(operation, success=False, latency_ms=(time.perf_counter() - started) * 1000)
            raise SupabaseRepositoryUnavailable("Hosted account provider is unavailable.") from exc
        latency = (time.perf_counter() - started) * 1000
        payload = _json_response(response)
        if int(getattr(response, "status_code", 0)) >= 400:
            self.health.record(operation, success=False, latency_ms=latency)
            if int(getattr(response, "status_code", 0)) in {400, 401, 403}:
                stage = "credential-provider-rejected" if operation == "auth" else "membership-provider-rejected"
                raise SupabaseAuthenticationError(
                    "Hosted sign-in could not be verified.",
                    stage=stage,
                )
            raise SupabaseRepositoryUnavailable("Hosted account provider rejected the request.")
        self.health.record(operation, success=True, latency_ms=latency, authenticated=operation == "auth")
        return payload

    def sign_in(self, email: str, password: str) -> dict[str, Any]:
        normalized_email = str(email or "").strip().lower()
        password_value = str(password or "")
        if (
            not _EMAIL_RE.fullmatch(normalized_email)
            or not password_value
            or len(password_value) > _MAX_AUTH_PASSWORD_LENGTH
        ):
            raise SupabaseAuthenticationError(
                "Hosted sign-in could not be verified.",
                stage="credential-shape-invalid",
            )
        payload = self._request(
            "POST",
            "/auth/v1/token?grant_type=password",
            headers=self._headers(),
            json={"email": normalized_email, "password": password_value},
        )
        return self._validate_token_payload(payload)

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        if not str(refresh_token or ""):
            raise SupabaseAuthenticationError("Hosted session expired.", stage="refresh-token-missing")
        payload = self._request(
            "POST",
            "/auth/v1/token?grant_type=refresh_token",
            headers=self._headers(),
            json={"refresh_token": str(refresh_token)},
        )
        return self._validate_token_payload(payload)

    def membership(self, access_token: str, user_id: str) -> dict[str, str]:
        payload = self._request(
            "GET",
            "/rest/v1/global_terminal_tenant_memberships",
            operation="read",
            headers=self._headers(access_token),
            params={
                "select": "tenant_id,role",
                "user_id": f"eq.{user_id}",
                "order": "created_at.asc,tenant_id.asc",
                "limit": "1",
            },
        )
        rows = payload if isinstance(payload, list) else []
        row = rows[0] if rows and isinstance(rows[0], dict) else {}
        tenant_id = str(row.get("tenant_id") or "")
        role = str(row.get("role") or "")
        if not tenant_id or role not in {"owner", "member", "viewer"}:
            raise SupabaseAuthenticationError(
                "Hosted account membership is unavailable.",
                stage="membership-row-missing",
            )
        return {"tenant_id": tenant_id, "role": role}

    def sign_out(self, access_token: str) -> None:
        if not access_token or not self.config.configured:
            return
        try:
            self._request(
                "POST",
                "/auth/v1/logout?scope=local",
                headers=self._headers(access_token),
                json={},
            )
        except SupabaseAccountError:
            return

    @staticmethod
    def _validate_token_payload(payload: Any) -> dict[str, Any]:
        row = payload if isinstance(payload, dict) else {}
        user = row.get("user") if isinstance(row.get("user"), dict) else {}
        access_token = str(row.get("access_token") or "")
        refresh_token = str(row.get("refresh_token") or "")
        user_id = str(user.get("id") or "")
        expires_in = max(60, min(int(row.get("expires_in") or 3600), 86_400))
        if not access_token or not refresh_token or not user_id:
            raise SupabaseAuthenticationError(
                "Hosted sign-in could not be verified.",
                stage="token-payload-invalid",
            )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "user_id": user_id,
            "email": str(user.get("email") or ""),
            "user_metadata": user.get("user_metadata") if isinstance(user.get("user_metadata"), dict) else {},
        }


class SupabaseHostedSessionManager:
    def __init__(self, auth: SupabaseAuthClient, *, ttl_seconds: int | None = None):
        self.auth = auth
        configured_ttl = ttl_seconds or int(
            os.getenv("GLOBAL_TERMINAL_HOSTED_SESSION_TTL_SECONDS", "86400") or 86400
        )
        self.ttl_seconds = max(300, min(int(configured_ttl), 604_800))
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(str(token).encode("utf-8")).hexdigest()

    def create(self, email: str, password: str, *, replace: str | None = None) -> SessionCredentials:
        token_payload = self.auth.sign_in(email, password)
        membership = self.auth.membership(token_payload["access_token"], token_payload["user_id"])
        if replace:
            self.revoke(replace)
        opaque_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(24)
        now = time.time()
        email_value = str(token_payload.get("email") or "")
        metadata = token_payload.get("user_metadata") or {}
        display_name = str(metadata.get("display_name") or metadata.get("full_name") or "").strip()
        if not display_name:
            display_name = email_value.split("@", 1)[0][:80] or "Research account"
        record = {
            "access_token": token_payload["access_token"],
            "refresh_token": token_payload["refresh_token"],
            "access_expires_at": now + int(token_payload["expires_in"]),
            "hard_expires_at": now + self.ttl_seconds,
            "csrf_token": csrf_token,
            "user_id": token_payload["user_id"],
            "tenant_id": membership["tenant_id"],
            "role": membership["role"],
            "display_name": display_name,
        }
        with self._lock:
            self._sessions[self._hash(opaque_token)] = record
        return SessionCredentials(
            session_token=opaque_token,
            csrf_token=csrf_token,
            expires_at=_safe_clock(record["hard_expires_at"]),
        )

    def _refresh_locked(self, key: str, record: dict[str, Any], now: float) -> dict[str, Any] | None:
        if now >= float(record["hard_expires_at"]):
            self._sessions.pop(key, None)
            return None
        if now < float(record["access_expires_at"]) - 60:
            return record
        try:
            refreshed = self.auth.refresh(str(record["refresh_token"]))
        except SupabaseAccountError:
            self._sessions.pop(key, None)
            return None
        if refreshed["user_id"] != record["user_id"]:
            self._sessions.pop(key, None)
            return None
        record.update(
            {
                "access_token": refreshed["access_token"],
                "refresh_token": refreshed["refresh_token"],
                "access_expires_at": now + int(refreshed["expires_in"]),
            }
        )
        return record

    def resolve(self, token: str | None) -> dict[str, Any]:
        if not token:
            return anonymous_context()
        key = self._hash(token)
        now = time.time()
        with self._lock:
            record = self._sessions.get(key)
            if not record:
                return anonymous_context(state="hosted-session-invalid")
            record = self._refresh_locked(key, record, now)
            if not record:
                return anonymous_context(state="hosted-session-expired")
            return {
                "state": "authenticated-hosted",
                "authenticated": True,
                "identity_provider": "supabase",
                "user_id": record["user_id"],
                "tenant_id": record["tenant_id"],
                "display_name": record["display_name"],
                "role": record["role"],
                "plan": "free",
                "session_expires_at": _safe_clock(record["access_expires_at"]),
                "_supabase_access_token": record["access_token"],
            }

    def validate_csrf(self, token: str | None, cookie: str | None, supplied: str | None) -> bool:
        if not token or not cookie or not supplied:
            return False
        with self._lock:
            record = self._sessions.get(self._hash(token))
            expected = str((record or {}).get("csrf_token") or "")
        return bool(expected and hmac.compare_digest(expected, str(cookie)) and hmac.compare_digest(expected, str(supplied)))

    def revoke(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            record = self._sessions.pop(self._hash(token), None)
        if record:
            self.auth.sign_out(str(record.get("access_token") or ""))

    def is_hosted(self, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            return self._hash(token) in self._sessions


def _access_token(context: dict[str, Any]) -> str:
    if context.get("identity_provider") != "supabase" or not context.get("authenticated"):
        raise SupabaseAuthenticationError("Hosted account session required.")
    token = str(context.get("_supabase_access_token") or "")
    if not token:
        raise SupabaseAuthenticationError("Hosted account session required.")
    return token


class SupabaseAccountDocumentRepository:
    def __init__(
        self,
        config: SupabaseAccountConfig | None = None,
        *,
        transport: HttpTransport | None = None,
        health: SupabaseRepositoryHealth | None = None,
    ):
        self.config = config or SupabaseAccountConfig.from_env()
        self.transport = transport or RequestsTransport()
        self._health = health or SupabaseRepositoryHealth(self.config)

    def _headers(self, context: dict[str, Any]) -> dict[str, str]:
        return {
            "apikey": self.config.publishable_key,
            "Authorization": f"Bearer {_access_token(context)}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, context: dict[str, Any], *, operation: str, **kwargs: Any) -> Any:
        if not self.config.configured:
            raise SupabaseRepositoryUnavailable("Hosted account repository is not configured.")
        started = time.perf_counter()
        try:
            response = self.transport.request(
                method,
                f"{self.config.url}{path}",
                headers=self._headers(context),
                timeout=self.config.timeout_seconds,
                **kwargs,
            )
        except SupabaseAuthenticationError:
            raise
        except Exception as exc:
            self._health.record(operation, success=False, latency_ms=(time.perf_counter() - started) * 1000)
            raise SupabaseRepositoryUnavailable("Hosted account repository is unavailable.") from exc
        latency = (time.perf_counter() - started) * 1000
        payload = _json_response(response)
        status = int(getattr(response, "status_code", 0))
        if status >= 400:
            self._health.record(operation, success=False, latency_ms=latency)
            if status in {401, 403}:
                raise SupabaseAuthenticationError("Hosted account session is not authorized.")
            if status == 409:
                raise SupabaseRepositoryConflict(0)
            raise SupabaseRepositoryUnavailable("Hosted account repository rejected the request.")
        self._health.record(operation, success=True, latency_ms=latency, authenticated=True)
        return payload

    def load(self, context: dict[str, Any]) -> dict[str, Any] | None:
        payload = self._request(
            "GET",
            "/rest/v1/global_terminal_account_documents",
            context,
            operation="read",
            params={
                "select": "document_id,document_key,payload,document_fingerprint,version,deleted,created_at,updated_at",
                "document_key": f"eq.{ACCOUNT_DOCUMENT_KEY}",
                "deleted": "eq.false",
                "limit": "1",
            },
        )
        rows = payload if isinstance(payload, list) else []
        row = rows[0] if rows and isinstance(rows[0], dict) else None
        if not row:
            return None
        return {
            "document_key": str(row.get("document_key") or ACCOUNT_DOCUMENT_KEY),
            "payload": row.get("payload") if isinstance(row.get("payload"), dict) else {},
            "fingerprint": str(row.get("document_fingerprint") or ""),
            "version": max(0, int(row.get("version") or 0)),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    def save(
        self,
        context: dict[str, Any],
        bundle: dict[str, Any],
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not _IDEMPOTENCY_RE.fullmatch(str(idempotency_key or "")):
            raise ValueError("Invalid account repository idempotency key.")
        fingerprint = str(bundle.get("fingerprint") or "")
        if not _FINGERPRINT_RE.fullmatch(fingerprint):
            raise ValueError("Invalid account repository fingerprint.")
        if any(key in bundle for key in ("tenant_id", "user_id", "owner_user_id")):
            raise ValueError("Account identity is server-derived.")
        payload = self._request(
            "POST",
            "/rest/v1/rpc/global_terminal_apply_account_document",
            context,
            operation="write",
            json={
                "p_document_key": ACCOUNT_DOCUMENT_KEY,
                "p_payload": bundle,
                "p_document_fingerprint": fingerprint,
                "p_expected_version": max(0, int(expected_version)),
                "p_idempotency_key": str(idempotency_key),
            },
        )
        row = payload[0] if isinstance(payload, list) and payload else payload
        result = row if isinstance(row, dict) else {}
        status = str(result.get("status") or "unavailable")
        current_version = max(0, int(result.get("version") or result.get("current_version") or 0))
        if status in {"conflict", "document-version-conflict"}:
            self._health.record("write", success=False, authenticated=True, conflict=True)
            raise SupabaseRepositoryConflict(current_version)
        if status not in {"applied", "deduped"}:
            raise SupabaseRepositoryUnavailable("Hosted account write was not confirmed.")
        return {
            "status": status,
            "version": current_version,
            "fingerprint": str(result.get("document_fingerprint") or fingerprint),
            "provider_call_count": 0,
        }

    def delete(
        self,
        context: dict[str, Any],
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not _IDEMPOTENCY_RE.fullmatch(str(idempotency_key or "")):
            raise ValueError("Invalid account repository idempotency key.")
        payload = self._request(
            "POST",
            "/rest/v1/rpc/global_terminal_delete_account_document",
            context,
            operation="write",
            json={
                "p_document_key": ACCOUNT_DOCUMENT_KEY,
                "p_expected_version": max(0, int(expected_version)),
                "p_idempotency_key": str(idempotency_key),
            },
        )
        row = payload[0] if isinstance(payload, list) and payload else payload
        result = row if isinstance(row, dict) else {}
        status = str(result.get("status") or "unavailable")
        if status in {"conflict", "document-version-conflict"}:
            raise SupabaseRepositoryConflict(
                int(result.get("version") or result.get("current_version") or 0)
            )
        if status not in {"deleted", "deduped", "not-found"}:
            raise SupabaseRepositoryUnavailable("Hosted account deletion was not confirmed.")
        return {"status": status, "version": int(result.get("version") or 0), "provider_call_count": 0}

    def health(self) -> dict[str, Any]:
        return self._health.public_snapshot()
