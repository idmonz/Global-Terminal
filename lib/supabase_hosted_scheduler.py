from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests

from .supabase_account_runtime import (
    HttpTransport,
    RequestsTransport,
    SupabaseAccountConfig,
    SupabaseAuthenticationError,
    SupabaseRepositoryConflict,
    SupabaseRepositoryUnavailable,
    _access_token,
)


SUPABASE_HOSTED_SCHEDULER_VERSION = "supabase_hosted_scheduler.v1"
_IDENTITY_FIELDS = {"tenant_id", "owner_user_id", "user_id", "lease_token", "lease_owner"}


def _hash(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _safe_schedule(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or _IDENTITY_FIELDS.intersection(value):
        raise ValueError("Hosted schedule identity and lease scope are server-derived.")
    allowed = {
        "schedule_id",
        "watchlist_id",
        "alert_rule_id",
        "state",
        "timezone",
        "cadence_minutes",
        "bounds",
        "next_due_at",
        "last_attempted_at",
        "last_completed_at",
        "last_run_id",
        "last_lkg_run_id",
        "consented_at",
        "enabled_at",
        "paused_at",
        "killed_at",
        "deleted_at",
        "version",
        "updated_at",
    }
    if set(value) - allowed:
        raise ValueError("Hosted schedule contains unsupported fields.")
    return {key: value.get(key) for key in allowed if key in value}


def _json(response: Any) -> Any:
    try:
        return response.json()
    except Exception as exc:
        raise SupabaseRepositoryUnavailable("Hosted scheduler returned an invalid response.") from exc


def _rpc_result(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        payload = payload["result"]
    return payload if isinstance(payload, dict) else {}


class SupabaseHostedSchedulerRepository:
    """User-JWT schedule materialization; never used for worker leases."""

    def __init__(
        self,
        config: SupabaseAccountConfig | None = None,
        *,
        transport: HttpTransport | None = None,
    ):
        self.config = config or SupabaseAccountConfig.from_env()
        self.transport = transport or RequestsTransport()

    def _request(self, method: str, path: str, context: dict[str, Any], **kwargs: Any) -> Any:
        if not self.config.configured:
            raise SupabaseRepositoryUnavailable("Hosted scheduler repository is not configured.")
        headers = {
            "apikey": self.config.publishable_key,
            "Authorization": f"Bearer {_access_token(context)}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            response = self.transport.request(
                method,
                f"{self.config.url}{path}",
                headers=headers,
                timeout=self.config.timeout_seconds,
                **kwargs,
            )
        except SupabaseAuthenticationError:
            raise
        except Exception as exc:
            raise SupabaseRepositoryUnavailable("Hosted scheduler repository is unavailable.") from exc
        payload = _json(response)
        status = int(getattr(response, "status_code", 0))
        if status in {401, 403}:
            raise SupabaseAuthenticationError("Hosted scheduler session is not authorized.")
        if status >= 400:
            raise SupabaseRepositoryUnavailable("Hosted scheduler repository rejected the request.")
        return payload

    def apply(self, context: dict[str, Any], schedule: dict[str, Any], *, expected_version: int) -> dict[str, Any]:
        payload = _rpc_result(
            self._request(
                "POST",
                "/rest/v1/rpc/global_terminal_apply_hosted_observation_schedule",
                context,
                json={"p_schedule": _safe_schedule(schedule), "p_expected_version": max(0, int(expected_version))},
            )
        )
        status = str(payload.get("status") or "unavailable")
        if status == "conflict":
            raise SupabaseRepositoryConflict(int(payload.get("current_version") or 0))
        if status not in {"applied", "deduped"}:
            raise SupabaseRepositoryUnavailable("Hosted schedule materialization was not confirmed.")
        return {
            "status": status,
            "version": int(payload.get("version") or 0),
            "state": str(payload.get("state") or schedule.get("state") or "disabled"),
            "provider_call_count": 0,
        }

    def read_contract_rows(self, context: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        schedules = self._request(
            "GET",
            "/rest/v1/global_terminal_hosted_observation_schedules",
            context,
            params={
                "select": "schedule_id,watchlist_resource_id,alert_rule_resource_id,state,timezone,cadence_minutes,max_symbols,max_provider_calls,max_attempts,timeout_seconds,next_due_at,last_attempted_at,last_completed_at,last_run_id,last_lkg_run_id,consented_at,enabled_at,paused_at,killed_at,deleted_at,version,updated_at",
                "state": "neq.deleted",
                "order": "updated_at.desc",
                "limit": "5",
            },
        )
        runs = self._request(
            "GET",
            "/rest/v1/global_terminal_hosted_observation_schedule_runs",
            context,
            params={
                "select": "scheduler_run_id,schedule_id,due_window_at,status,lease_acquired_at,lease_expires_at,heartbeat_at,attempt_count,observation_run_id,evaluation_run_id,trigger_count,provider_call_budget,provider_call_count,provider,source_url,source_status,observed_at,retrieved_at,evaluated_at,triggered_at,result,error_code,duration_ms,lkg_run_id,completed_at,created_at,updated_at",
                "order": "created_at.desc",
                "limit": "20",
            },
        )
        return {
            "schedules": schedules if isinstance(schedules, list) else [],
            "runs": runs if isinstance(runs, list) else [],
        }


@dataclass(frozen=True)
class SupabaseHostedSchedulerServiceConfig:
    url: str
    secret_key: str = field(repr=False)
    timeout_seconds: float = 12.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", str(self.url or "").strip().rstrip("/"))
        object.__setattr__(self, "secret_key", str(self.secret_key or "").strip())
        object.__setattr__(self, "timeout_seconds", max(2.0, min(float(self.timeout_seconds), 30.0)))

    @property
    def configured(self) -> bool:
        parsed = urlparse(self.url)
        secure_remote = parsed.scheme == "https" and bool(parsed.hostname)
        local_runtime = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        return bool((secure_remote or local_runtime) and len(self.secret_key) >= 20)

    @classmethod
    def from_env(cls) -> "SupabaseHostedSchedulerServiceConfig":
        return cls(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SECRET_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            float(os.getenv("GLOBAL_TERMINAL_SUPABASE_TIMEOUT_SECONDS", "12") or 12),
        )


class SupabaseHostedSchedulerServiceClient:
    """Service-only scheduler RPC client. Secret values never enter public contracts."""

    def __init__(
        self,
        config: SupabaseHostedSchedulerServiceConfig | None = None,
        *,
        transport: HttpTransport | None = None,
    ):
        self.config = config or SupabaseHostedSchedulerServiceConfig.from_env()
        self.transport = transport or RequestsTransport(requests.Session())

    def _headers(self) -> dict[str, str]:
        headers = {
            "apikey": self.config.secret_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        # New sb_secret_* API keys are not JWTs and must not be sent as a
        # bearer token. Legacy service-role keys remain JWT based.
        if not self.config.secret_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self.config.secret_key}"
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.config.configured:
            raise SupabaseRepositoryUnavailable("Hosted scheduler service credential is not configured.")
        try:
            response = self.transport.request(
                method,
                f"{self.config.url}{path}",
                headers=self._headers(),
                timeout=self.config.timeout_seconds,
                **kwargs,
            )
        except Exception as exc:
            raise SupabaseRepositoryUnavailable("Hosted scheduler service is unavailable.") from exc
        payload = _json(response)
        if int(getattr(response, "status_code", 0)) >= 400:
            raise SupabaseRepositoryUnavailable("Hosted scheduler service request was rejected.")
        return payload

    def claim(self, worker_id: str, *, lease_seconds: int = 120) -> dict[str, Any]:
        lease_token = secrets.token_urlsafe(32)
        payload = _rpc_result(
            self._request(
                "POST",
                "/rest/v1/rpc/global_terminal_claim_hosted_observation_schedule",
                json={
                    "p_worker_hash": _hash(worker_id),
                    "p_lease_token_hash": _hash(lease_token),
                    "p_lease_seconds": max(30, min(int(lease_seconds), 300)),
                },
            )
        )
        if payload.get("claimed") is True:
            payload["_lease_token"] = lease_token
        return payload

    def heartbeat(self, claim: dict[str, Any], *, lease_seconds: int = 120) -> dict[str, Any]:
        return _rpc_result(
            self._request(
                "POST",
                "/rest/v1/rpc/global_terminal_heartbeat_hosted_observation_schedule",
                json={
                    "p_scheduler_run_id": str(claim.get("scheduler_run_id") or ""),
                    "p_lease_token_hash": _hash(str(claim.get("_lease_token") or "")),
                    "p_lease_seconds": max(30, min(int(lease_seconds), 300)),
                },
            )
        )

    def load_account_document(self, claim: dict[str, Any]) -> dict[str, Any]:
        payload = self._request(
            "GET",
            "/rest/v1/global_terminal_account_documents",
            params={
                "select": "document_id,payload,document_fingerprint,version,deleted",
                "document_id": f"eq.{claim.get('account_document_id')}",
                "tenant_id": f"eq.{claim.get('tenant_id')}",
                "owner_user_id": f"eq.{claim.get('owner_user_id')}",
                "deleted": "eq.false",
                "limit": "1",
            },
        )
        rows = payload if isinstance(payload, list) else []
        row = rows[0] if rows and isinstance(rows[0], dict) else None
        if not row or not isinstance(row.get("payload"), dict):
            raise SupabaseRepositoryUnavailable("Hosted account document is unavailable for the claimed schedule.")
        return {
            "document_id": str(row.get("document_id") or ""),
            "payload": row["payload"],
            "fingerprint": str(row.get("document_fingerprint") or ""),
            "version": int(row.get("version") or 0),
        }

    def persist_account_document(self, claim: dict[str, Any], bundle: dict[str, Any], *, expected_version: int) -> dict[str, Any]:
        return _rpc_result(
            self._request(
                "POST",
                "/rest/v1/rpc/global_terminal_apply_scheduler_account_document",
                json={
                    "p_scheduler_run_id": str(claim.get("scheduler_run_id") or ""),
                    "p_lease_token_hash": _hash(str(claim.get("_lease_token") or "")),
                    "p_payload": bundle,
                    "p_document_fingerprint": str(bundle.get("fingerprint") or ""),
                    "p_expected_version": max(0, int(expected_version)),
                    "p_idempotency_key": f"phase6q-document-{str(claim.get('scheduler_run_id') or '')[:72]}",
                },
            )
        )

    def finish(self, claim: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        return _rpc_result(
            self._request(
                "POST",
                "/rest/v1/rpc/global_terminal_finish_hosted_observation_schedule",
                json={
                    "p_scheduler_run_id": str(claim.get("scheduler_run_id") or ""),
                    "p_lease_token_hash": _hash(str(claim.get("_lease_token") or "")),
                    "p_result": result,
                },
            )
        )

    def public_readiness(self) -> dict[str, Any]:
        return {
            "contract_version": SUPABASE_HOSTED_SCHEDULER_VERSION,
            "configured": self.config.configured,
            "source_status": "configured-unverified" if self.config.configured else "missing-key",
            "hosted_scheduler_verified": False,
            "configured_is_not_verified": True,
            "provider_call_count": 0,
        }
