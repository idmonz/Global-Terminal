from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_phase6m_api_envelope_is_json_safe_source_linked_and_bounded():
    from lib.api_contracts import build_api_attention_desk_payload, validate_api_payload
    from lib.attention_desk import build_attention_desk_contract

    contract = build_attention_desk_contract(
        news_rows=[
            {
                "title": "Named public report",
                "provider": "public-rss",
                "source_url": "https://example.test/report",
                "source_status": "cached",
                "published_at": "2026-07-10T00:00:00+00:00",
                "fetched_at": "2026-07-10T00:05:00+00:00",
                "severity": "material",
                "confidence": 0.7,
                "caveat": "One source.",
                "data_gap": "No independent confirmation.",
            }
        ],
        mode="fixture",
    )
    payload = build_api_attention_desk_payload(contract)
    valid, issues = validate_api_payload(payload)

    assert valid, issues
    assert payload["payload_type"] == "attention_desk"
    assert payload["data"]["attention_desk_version"] == "attention_desk.v1"
    assert payload["summary"]["provider_call_count"] == 0
    assert payload["data"]["digest"]["bounded"] is True
    assert payload["source_status"][0]["source_url"] == "https://example.test/report"
    encoded = json.dumps(payload).lower()
    assert "tenant_id" not in encoded
    assert "owner_user_id" not in encoded


def test_phase6m_fixture_export_contains_attention_desk_contract(tmp_path: Path):
    from scripts.export_api_fixtures import export_api_fixtures

    written = export_api_fixtures(tmp_path)
    target = tmp_path / "attention-desk.json"
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert target in written
    assert payload["payload_type"] == "attention_desk"
    assert payload["data"]["summary"]["visible_count"] >= 3
    assert payload["data"]["provider_call_count"] == 0
    assert len(json.dumps(payload).encode("utf-8")) <= 50_000


def test_phase6m_public_route_composes_from_saved_evidence_without_provider_calls(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from backend.api import app as api_module

    def forbidden(*args, **kwargs):
        raise AssertionError("Attention compose contacted a market provider")

    monkeypatch.setattr("lib.live_feeds.fetch_live_news_feed", forbidden)
    client = TestClient(api_module.create_app())
    response = client.get("/api/attention-desk?mode=fixture")

    assert response.status_code == 200
    payload = response.json()
    assert payload["payload_type"] == "attention_desk"
    assert payload["summary"]["provider_call_count"] == 0
    assert payload["data"]["readiness"]["hosted_persistence"] == "unavailable"


def _signin(client, alias: str) -> str:
    response = client.post(
        "/api/account/local-session",
        headers={"origin": "http://testserver"},
        json={"alias": alias, "return_to": "/?view=attention-desk"},
    )
    assert response.status_code == 201
    csrf = client.cookies.get("gt_csrf")
    assert csrf
    return csrf


def test_phase6m_account_attention_review_policy_checkpoint_and_ab_isolation(monkeypatch, tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from backend.api import app as api_module

    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH", str(tmp_path / "account.db"))
    api_module.reset_identity_runtime_for_tests(tmp_path / "account.db")
    app = api_module.create_app()
    account_a = TestClient(app)
    account_b = TestClient(app)
    csrf_a = _signin(account_a, "analyst-a")
    csrf_b = _signin(account_b, "analyst-b")

    first_a = account_a.get("/api/account/attention-desk?mode=fixture")
    assert first_a.status_code == 200
    row = first_a.json()["data"]["items"][0]
    fingerprint = row["fingerprint"]
    reviewed = account_a.patch(
        f"/api/account/attention-desk/items/{fingerprint}",
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
        json={"action": "review", "expected_version": 0},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["data"]["review_state"] == "reviewed"

    second_a = account_a.get("/api/account/attention-desk?mode=fixture").json()
    second_b = account_b.get("/api/account/attention-desk?mode=fixture").json()
    state_a = next(item for item in second_a["data"]["items"] if item["fingerprint"] == fingerprint)
    state_b = next(item for item in second_b["data"]["items"] if item["fingerprint"] == fingerprint)
    assert state_a["review_state"] == "reviewed"
    assert state_b["review_state"] == "new"

    policy = account_a.put(
        "/api/account/attention-desk/policy",
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
        json={
            "minimum_severity": "high",
            "included_change_kinds": ["new-evidence", "source-degradation"],
            "source_health_handling": "include",
            "expected_version": 0,
        },
    )
    assert policy.status_code == 200
    assert policy.json()["data"]["version"] == 1
    conflict = account_a.put(
        "/api/account/attention-desk/policy",
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
        json={
            "minimum_severity": "material",
            "included_change_kinds": ["new-evidence"],
            "source_health_handling": "include",
            "expected_version": 0,
        },
    )
    assert conflict.status_code == 409

    checkpoint = account_a.post(
        "/api/account/attention-desk/checkpoint",
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
        json={"expected_version": 0},
    )
    assert checkpoint.status_code == 200
    assert checkpoint.json()["data"]["provider_clock_unchanged"] is True
    assert csrf_b != csrf_a


def test_phase6m_account_attention_rejects_client_identity_and_has_bounded_audit(monkeypatch, tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from backend.api import app as api_module

    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "true")
    api_module.reset_identity_runtime_for_tests(tmp_path / "account.db")
    client = TestClient(api_module.create_app())
    csrf = _signin(client, "analyst-a")

    response = client.put(
        "/api/account/attention-desk/policy",
        headers={"origin": "http://testserver", "x-csrf-token": csrf},
        json={
            "tenant_id": "client-controlled",
            "minimum_severity": "high",
            "included_change_kinds": ["new-evidence"],
            "source_health_handling": "include",
            "expected_version": 0,
        },
    )
    assert response.status_code == 422
    audit = client.get("/api/account/attention-desk/audit?limit=500")
    assert audit.status_code == 200
    assert len(audit.json()["data"]) <= 100
