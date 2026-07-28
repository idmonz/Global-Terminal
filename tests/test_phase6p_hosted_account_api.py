from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


HOSTED_USER = "22222222-2222-4222-8222-222222222222"
HOSTED_TENANT = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


class FakeHostedSessionManager:
    ttl_seconds = 3600

    def __init__(self):
        self.active = False
        self.revoked = False
        self.role = "owner"

    def create(self, email: str, password: str, *, replace: str | None = None):
        del replace
        assert email == "analyst@example.test"
        assert password == "correct-password"
        from lib.identity_tenancy import SessionCredentials

        self.active = True
        return SessionCredentials("opaque-hosted-session", "hosted-csrf", "2026-07-15T10:00:00+00:00")

    def resolve(self, token: str | None) -> dict[str, Any]:
        if not self.active or token != "opaque-hosted-session":
            from lib.identity_tenancy import anonymous_context

            return anonymous_context(state="hosted-session-invalid")
        return {
            "state": "authenticated-hosted",
            "authenticated": True,
            "identity_provider": "supabase",
            "user_id": HOSTED_USER,
            "tenant_id": HOSTED_TENANT,
            "display_name": "Hosted analyst",
            "role": self.role,
            "plan": "free",
            "session_expires_at": "2026-07-15T10:00:00+00:00",
            "_supabase_access_token": "must-never-leak",
        }

    def validate_csrf(self, token: str | None, cookie: str | None, supplied: str | None) -> bool:
        return token == "opaque-hosted-session" and cookie == supplied == "hosted-csrf"

    def revoke(self, token: str | None) -> None:
        if token == "opaque-hosted-session":
            self.active = False
            self.revoked = True


class RejectingHostedSessionManager(FakeHostedSessionManager):
    def create(self, email: str, password: str, *, replace: str | None = None):
        del email, password, replace
        from lib.supabase_account_runtime import SupabaseAuthenticationError

        raise SupabaseAuthenticationError(
            "Hosted sign-in could not be verified.",
            stage="membership-provider-rejected",
        )


class FakeContinuity:
    def __init__(self):
        self.sync_operations: list[str] = []

    @staticmethod
    def _health() -> dict[str, Any]:
        return {
            "provider": "supabase",
            "configured": True,
            "contacted": True,
            "authenticated": True,
            "rls_verified": True,
            "read_successful": True,
            "write_successful": True,
            "hosted_verified": True,
            "source_status": "hosted-ready",
            "provider_call_count": 0,
        }

    def restore(self, context: dict[str, Any], *, prefer_remote: bool = False) -> dict[str, Any]:
        assert context["tenant_id"] == HOSTED_TENANT
        return {
            "status": "hosted-ready",
            "restored_count": 3 if prefer_remote else 2,
            "remote_version": 4,
            "remote_contacted": True,
            "provider_call_count": 0,
        }

    def status(self, context: dict[str, Any]) -> dict[str, Any]:
        assert context["tenant_id"] == HOSTED_TENANT
        return {
            "state": "hosted-ready",
            "pending_count": 0,
            "conflict_count": 0,
            "last_restore_at": "2026-07-15T09:00:00+00:00",
            "last_sync_at": "2026-07-15T09:01:00+00:00",
            "last_recovery_at": None,
            "last_failure_at": None,
            "repository": self._health(),
            "provider_call_count": 0,
        }

    def sync(self, context: dict[str, Any], *, idempotency_key: str) -> dict[str, Any]:
        assert context["tenant_id"] == HOSTED_TENANT
        self.sync_operations.append(idempotency_key)
        return {
            "status": "applied",
            "remote_version": 5,
            "remote_contacted": True,
            "provider_call_count": 0,
        }

    def replay(self, context: dict[str, Any]) -> dict[str, Any]:
        assert context["tenant_id"] == HOSTED_TENANT
        return {"status": "recovered", "applied_count": 1, "pending_count": 0, "conflict_count": 0}

    def resolve_conflict(
        self,
        context: dict[str, Any],
        *,
        strategy: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        assert context["tenant_id"] == HOSTED_TENANT
        assert strategy in {"keep-local", "use-hosted"}
        assert idempotency_key
        return {"status": "applied", "resolution": strategy, "remote_version": 6}

    def export(self, context: dict[str, Any]) -> dict[str, Any]:
        assert context["tenant_id"] == HOSTED_TENANT
        return {
            "account_continuity_version": "account_continuity.v1",
            "tables": {},
            "row_count": 0,
            "excluded_fields": ["credentials", "identity"],
        }

    def import_backup(
        self,
        context: dict[str, Any],
        bundle: dict[str, Any],
        *,
        strategy: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        assert context["tenant_id"] == HOSTED_TENANT
        assert bundle["account_continuity_version"] == "account_continuity.v1"
        assert strategy in {"merge", "replace"}
        assert idempotency_key
        return {"status": "applied", "strategy": strategy, "restore": {"status": "restored"}}

    def delete_hosted(self, context: dict[str, Any], *, idempotency_key: str) -> dict[str, Any]:
        assert context["tenant_id"] == HOSTED_TENANT
        assert idempotency_key
        return {"status": "deleted", "local_retained": True, "remote_version": 7}


def _hosted_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api import app as backend_app

    monkeypatch.setenv("SUPABASE_URL", "https://project.example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")
    monkeypatch.setenv("GLOBAL_TERMINAL_HOSTED_AUTH_ENABLED", "true")
    monkeypatch.setenv("GLOBAL_TERMINAL_ACCOUNT_CONTINUITY_ENABLED", "true")
    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "false")
    backend_app.reset_identity_runtime_for_tests(tmp_path / "account.db")
    manager = FakeHostedSessionManager()
    continuity = FakeContinuity()
    backend_app.configure_hosted_account_runtime_for_tests(manager, continuity)
    return TestClient(backend_app.create_app()), manager, continuity


def test_phase6p_hosted_sign_in_restores_and_never_exposes_credentials(monkeypatch, tmp_path: Path):
    client, manager, _ = _hosted_client(monkeypatch, tmp_path)
    response = client.post(
        "/api/account/hosted-session",
        json={"email": "analyst@example.test", "password": "correct-password", "return_to": "/?view=attention-desk"},
        headers={"Origin": "http://testserver"},
    )
    assert response.status_code == 201
    assert "HttpOnly" in response.headers.get("set-cookie", "")
    data = response.json()["data"]
    assert data["identity"]["identity_provider"] == "supabase"
    assert data["restore"]["status"] == "hosted-ready"
    assert data["persistence"]["hosted_verified"] is True
    encoded = response.text.lower()
    assert "correct-password" not in encoded
    assert "must-never-leak" not in encoded
    assert HOSTED_USER.lower() not in encoded
    assert HOSTED_TENANT.lower() not in encoded
    assert manager.active is True


def test_phase6p_hosted_sign_in_rejects_forged_identity(monkeypatch, tmp_path: Path):
    client, manager, _ = _hosted_client(monkeypatch, tmp_path)
    response = client.post(
        "/api/account/hosted-session",
        json={
            "email": "analyst@example.test",
            "password": "correct-password",
            "tenant_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        },
        headers={"Origin": "http://testserver"},
    )
    assert response.status_code == 422
    assert manager.active is False


def test_phase6p_auth_stage_is_available_only_in_explicit_loopback_qa(monkeypatch, tmp_path: Path):
    client, _, continuity = _hosted_client(monkeypatch, tmp_path)
    from backend.api import app as backend_app

    backend_app.configure_hosted_account_runtime_for_tests(
        RejectingHostedSessionManager(),
        continuity,
    )
    body = {"email": "analyst@example.test", "password": "correct-password"}
    headers = {"Origin": "http://testserver"}

    monkeypatch.delenv("GLOBAL_TERMINAL_QA_AUTH_DIAGNOSTICS", raising=False)
    public = client.post("/api/account/hosted-session", json=body, headers=headers)
    assert public.status_code == 401
    assert public.json() == {"detail": "Hosted sign-in could not be verified."}
    assert "X-Global-Terminal-QA-Auth-Stage" not in public.headers

    monkeypatch.setenv("GLOBAL_TERMINAL_QA_AUTH_DIAGNOSTICS", "phase6p-recovery")
    diagnostic = client.post("/api/account/hosted-session", json=body, headers=headers)
    assert diagnostic.status_code == 401
    assert diagnostic.json() == {"detail": "Hosted sign-in could not be verified."}
    assert diagnostic.headers["X-Global-Terminal-QA-Auth-Stage"] == "membership-provider-rejected"


def test_phase6p_hosted_viewer_session_is_read_only(monkeypatch, tmp_path: Path):
    client, manager, _ = _hosted_client(monkeypatch, tmp_path)
    manager.role = "viewer"
    assert client.post(
        "/api/account/hosted-session",
        json={"email": "analyst@example.test", "password": "correct-password"},
        headers={"Origin": "http://testserver"},
    ).status_code == 201
    csrf = client.cookies.get("gt_csrf")
    read = client.get("/api/account/continuity")
    assert read.status_code == 200
    write = client.put(
        "/api/account/preferences/analyst-layout",
        json={"expected_version": 0, "value": {"preset": "research"}},
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
    )
    assert write.status_code == 403
    assert write.json()["detail"] == "Account role is read-only."


def test_phase6p_mutation_and_continuity_controls_use_hosted_csrf(monkeypatch, tmp_path: Path):
    client, manager, continuity = _hosted_client(monkeypatch, tmp_path)
    signed_in = client.post(
        "/api/account/hosted-session",
        json={"email": "analyst@example.test", "password": "correct-password"},
        headers={"Origin": "http://testserver"},
    )
    assert signed_in.status_code == 201
    csrf = client.cookies.get("gt_csrf")
    headers = {"Origin": "http://testserver", "X-CSRF-Token": csrf}

    rejected = client.put(
        "/api/account/preferences/analyst-layout",
        json={"expected_version": 0, "value": {"preset": "research"}},
        headers={"Origin": "http://testserver"},
    )
    assert rejected.status_code == 403

    saved = client.put(
        "/api/account/preferences/analyst-layout",
        json={"expected_version": 0, "value": {"preset": "research"}},
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["data"]["persistence"]["status"] == "applied"
    assert continuity.sync_operations

    status = client.get("/api/account/continuity")
    assert status.status_code == 200
    assert status.json()["data"]["state"] == "hosted-ready"
    replay = client.post("/api/account/continuity/replay", json={}, headers=headers)
    assert replay.json()["data"]["status"] == "recovered"
    resolved = client.post(
        "/api/account/continuity/resolve",
        json={"strategy": "keep-local", "idempotency_key": "phase6p-resolve-001"},
        headers=headers,
    )
    assert resolved.json()["data"]["resolution"] == "keep-local"
    exported = client.get("/api/account/continuity/export")
    assert "credentials" in exported.json()["data"]["excluded_fields"]
    imported = client.post(
        "/api/account/continuity/import",
        json={
            "bundle": {
                "account_continuity_version": "account_continuity.v1",
                "tables": {},
                "fingerprint": "f" * 64,
            },
            "strategy": "merge",
            "idempotency_key": "phase6p-backup-import-001",
        },
        headers=headers,
    )
    assert imported.status_code == 200
    assert imported.json()["data"]["restore"]["status"] == "restored"
    deleted = client.delete(
        "/api/account/continuity?idempotency_key=phase6p-delete-001",
        headers=headers,
    )
    assert deleted.json()["data"]["local_retained"] is True

    signed_out = client.post("/api/account/signout", json={}, headers=headers)
    assert signed_out.status_code == 200
    assert manager.revoked is True
    assert client.get("/api/account/session").json()["data"]["identity"]["authenticated"] is False
