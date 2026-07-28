from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


NOW = datetime(2026, 7, 10, 1, 0, tzinfo=timezone.utc)


def test_phase6j_anonymous_contract_is_local_and_provider_call_free():
    from lib.identity_tenancy import build_account_workspace_contract, anonymous_context

    payload = build_account_workspace_contract(anonymous_context(), provider_calls=0)
    assert payload["identity"]["state"] == "anonymous-local"
    assert payload["identity"]["authenticated"] is False
    assert payload["persistence"]["hosted_verified"] is False
    assert payload["summary"]["provider_calls"] == 0
    assert payload["entitlements"]["checkout_enabled"] is False


def test_phase6j_repository_enforces_tenant_on_every_operation(tmp_path: Path):
    from lib.identity_tenancy import SQLiteTenantPreferenceAdapter, local_test_context

    adapter = SQLiteTenantPreferenceAdapter(tmp_path / "tenant.db")
    account_a = local_test_context("analyst-a")
    account_b = local_test_context("analyst-b")
    saved = adapter.save(
        account_a,
        "analyst-layout",
        {"preset": "research", "split": 61},
        expected_version=0,
    )
    assert adapter.get(account_a, "analyst-layout")["resource_id"] == saved["resource_id"]
    assert adapter.get(account_b, "analyst-layout") is None
    assert adapter.get_by_id(account_b, saved["resource_id"]) is None
    assert adapter.delete(account_b, saved["resource_id"], expected_version=1) is False
    assert adapter.export(account_b)["preferences"] == []


def test_phase6j_client_cannot_select_authoritative_tenant():
    from lib.identity_tenancy import validate_preference_body

    with pytest.raises(ValueError, match="server-derived"):
        validate_preference_body(
            {"tenant_id": "tenant_other", "value": {"preset": "research"}}
        )
    with pytest.raises(ValueError, match="server-derived"):
        validate_preference_body(
            {"user_id": "user_other", "value": {"preset": "research"}}
        )


def test_phase6j_optimistic_concurrency_reports_conflict(tmp_path: Path):
    from lib.identity_tenancy import PreferenceConflict, SQLiteTenantPreferenceAdapter, local_test_context

    adapter = SQLiteTenantPreferenceAdapter(tmp_path / "tenant.db")
    context = local_test_context("analyst-a")
    first = adapter.save(context, "analyst-layout", {"split": 58}, expected_version=0)
    second = adapter.save(
        context,
        "analyst-layout",
        {"split": 64},
        expected_version=first["version"],
    )
    assert second["version"] == 2
    with pytest.raises(PreferenceConflict) as conflict:
        adapter.save(context, "analyst-layout", {"split": 52}, expected_version=1)
    assert conflict.value.current_version == 2


def test_phase6j_session_rotation_expiry_and_revocation():
    from lib.identity_tenancy import SessionManager

    manager = SessionManager(ttl_seconds=60)
    first = manager.create("analyst-a", now=NOW)
    assert manager.resolve(first.session_token, now=NOW)["authenticated"] is True
    rotated = manager.create("analyst-a", now=NOW + timedelta(seconds=1), replace=first.session_token)
    assert rotated.session_token != first.session_token
    assert manager.resolve(first.session_token, now=NOW + timedelta(seconds=2))["authenticated"] is False
    assert manager.resolve(rotated.session_token, now=NOW + timedelta(seconds=62))["state"] == "expired"
    manager.revoke(rotated.session_token)
    assert manager.resolve(rotated.session_token, now=NOW + timedelta(seconds=3))["authenticated"] is False


def test_phase6j_csrf_and_return_url_validation():
    from lib.identity_tenancy import csrf_matches, validate_return_to

    assert csrf_matches("session-csrf", "session-csrf") is True
    assert csrf_matches("session-csrf", "other") is False
    assert validate_return_to("/?view=analyst-workspace&symbol=AAPL").startswith("/")
    for unsafe in ("https://evil.example", "//evil.example", "/\\evil", "javascript:alert(1)"):
        with pytest.raises(ValueError):
            validate_return_to(unsafe)


def test_phase6j_supabase_stays_unverified_without_live_configuration(monkeypatch):
    from lib.identity_tenancy import persistence_provider_health

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    health = persistence_provider_health()
    assert health["provider"] == "supabase"
    assert health["configured"] is False
    assert health["contacted"] is False
    assert health["hosted_verified"] is False
    assert health["source_status"] == "missing-key"


def test_phase6j_contract_redacts_tokens_paths_and_private_fields():
    from lib.identity_tenancy import public_account_payload

    payload = public_account_payload(
        {
            "session_token": "never-public",
            "csrf_token": "never-public-either",
            "service_role_key": "secret-value",
            "db_path": "C:/private/research.db",
            "identity": {"state": "authenticated-local-test"},
        }
    )
    encoded = str(payload).lower()
    assert "never-public" not in encoded
    assert "secret-value" not in encoded
    assert "c:/private" not in encoded


def test_phase6j_api_session_csrf_preference_and_signout(monkeypatch, tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api import app as backend_app

    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "true")
    backend_app.reset_identity_runtime_for_tests(tmp_path / "account.db")
    client = TestClient(backend_app.create_app())

    anonymous = client.get("/api/account/session")
    assert anonymous.status_code == 200
    assert anonymous.json()["data"]["identity"]["state"] == "anonymous-local"

    signed_in = client.post(
        "/api/account/local-session",
        json={"alias": "analyst-a", "return_to": "/?view=analyst-workspace"},
        headers={"Origin": "http://testserver"},
    )
    assert signed_in.status_code == 201
    assert "HttpOnly" in signed_in.headers.get("set-cookie", "")
    session = client.get("/api/account/session").json()["data"]
    assert session["identity"]["state"] == "authenticated-local-test"
    csrf = client.cookies.get("gt_csrf")
    assert csrf

    rejected = client.put(
        "/api/account/preferences/analyst-layout",
        json={"expected_version": 0, "value": {"preset": "research"}},
    )
    assert rejected.status_code == 403

    saved = client.put(
        "/api/account/preferences/analyst-layout",
        json={"expected_version": 0, "value": {"preset": "research", "split": 63}},
        headers={"X-CSRF-Token": csrf, "Origin": "http://testserver"},
    )
    assert saved.status_code == 200
    assert saved.json()["data"]["version"] == 1
    restored = client.get("/api/account/preferences/analyst-layout")
    assert restored.json()["data"]["value"]["split"] == 63

    conflict = client.put(
        "/api/account/preferences/analyst-layout",
        json={"expected_version": 0, "value": {"split": 40}},
        headers={"X-CSRF-Token": csrf, "Origin": "http://testserver"},
    )
    assert conflict.status_code == 409

    signed_out = client.post(
        "/api/account/signout",
        json={},
        headers={"X-CSRF-Token": csrf, "Origin": "http://testserver"},
    )
    assert signed_out.status_code == 200
    assert client.get("/api/account/session").json()["data"]["identity"]["authenticated"] is False


def test_phase6j_api_rejects_cross_tenant_body_and_unsafe_redirect(monkeypatch, tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api import app as backend_app

    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "true")
    backend_app.reset_identity_runtime_for_tests(tmp_path / "account.db")
    client = TestClient(backend_app.create_app())
    assert client.post(
        "/api/account/local-session",
        json={"alias": "analyst-a", "return_to": "https://evil.example"},
        headers={"Origin": "http://testserver"},
    ).status_code == 422

    client.post(
        "/api/account/local-session",
        json={"alias": "analyst-a", "return_to": "/"},
        headers={"Origin": "http://testserver"},
    )
    csrf = client.cookies.get("gt_csrf")
    response = client.put(
        "/api/account/preferences/analyst-layout",
        json={"tenant_id": "tenant_b", "expected_version": 0, "value": {}},
        headers={"X-CSRF-Token": csrf, "Origin": "http://testserver"},
    )
    assert response.status_code == 422
