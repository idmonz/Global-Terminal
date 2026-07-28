from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


NOW = datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)


def _signin(client, alias: str) -> str:
    response = client.post(
        "/api/account/local-session",
        headers={"origin": "http://testserver"},
        json={"alias": alias, "return_to": "/?view=alert-manager"},
    )
    assert response.status_code == 201
    csrf = client.cookies.get("gt_csrf")
    assert csrf
    return csrf


def _seed(db_path: Path) -> str:
    from lib.identity_tenancy import local_test_context
    from lib.research_workspace_db import execute_query, json_dumps

    context = local_test_context("analyst-a")
    tenant_id, user_id = context["tenant_id"], context["user_id"]
    watchlist_id = "twl_phase6o_api"
    timestamp = NOW.isoformat()
    execute_query(
        "INSERT INTO tenant_watchlists (resource_id, tenant_id, owner_user_id, name, source_key, source_fingerprint, version, active, created_at, updated_at) VALUES (?, ?, ?, 'API Alerts', 'phase6o-api', 'phase6o-api-fp', 1, 1, ?, ?)",
        (watchlist_id, tenant_id, user_id, timestamp, timestamp), db_path=db_path,
    )
    execute_query(
        "INSERT INTO tenant_watchlist_items (resource_id, tenant_id, watchlist_resource_id, symbol, asset_class, display_name, exchange, position, provider, source_url, source_status, observed_at, retrieved_at, evidence_json, version, active, created_at, updated_at) VALUES ('twi_phase6o_api', ?, ?, 'AAPL', 'equity', 'Apple Inc.', 'NASDAQ', 0, 'test-provider', 'https://example.test/aapl', 'live/fresh', ?, ?, '{}', 1, 1, ?, ?)",
        (tenant_id, watchlist_id, timestamp, timestamp, timestamp, timestamp), db_path=db_path,
    )
    execute_query(
        "INSERT INTO tenant_observation_runs (run_id, tenant_id, owner_user_id, watchlist_resource_id, watchlist_name, idempotency_key, request_fingerprint, status, requested_symbols_json, requested_count, completed_count, provider_call_budget, provider_call_count, session_json, provider_plan_json, provider_states_json, missing_capabilities_json, diff_json, attempted_at, started_at, observation_started_at, observation_ended_at, retrieved_at, completed_at, duration_ms, version, created_at, updated_at) VALUES ('obsrun_phase6o_api', ?, ?, ?, 'API Alerts', 'phase6o-api-seed', 'seed-fp', 'completed', '[\"AAPL\"]', 1, 1, 16, 1, '{}', '{}', '[]', '[]', '{}', ?, ?, ?, ?, ?, ?, 5, 1, ?, ?)",
        (tenant_id, user_id, watchlist_id, timestamp, timestamp, timestamp, timestamp, timestamp, timestamp, timestamp, timestamp), db_path=db_path,
    )
    payload = {"symbol": "AAPL", "quote": {"last_price": 212.5, "change_pct": 2.4}, "confidence": 0.9}
    execute_query(
        "INSERT INTO tenant_observation_snapshots (snapshot_id, tenant_id, owner_user_id, run_id, watchlist_resource_id, symbol, asset_class, snapshot_status, source_status, observed_at, retrieved_at, provider, source_url, confidence, content_hash, payload_json, caveat, data_gap, created_at) VALUES ('obssnap_phase6o_api', ?, ?, 'obsrun_phase6o_api', ?, 'AAPL', 'equity', 'fresh', 'live/fresh', ?, ?, 'test-provider', 'https://example.test/aapl', 0.9, 'api-snapshot-hash', ?, 'Delayed public data.', 'No real-time entitlement.', ?)",
        (tenant_id, user_id, watchlist_id, timestamp, timestamp, json_dumps(payload), timestamp), db_path=db_path,
    )
    return watchlist_id


def _rule(watchlist_id: str) -> dict:
    return {
        "watchlist_id": watchlist_id,
        "symbol": "AAPL",
        "rule_type": "price_above",
        "threshold": 200,
        "threshold_unit": "USD",
        "frequency": "15m",
        "session_policy": "market-aware",
        "cooldown_minutes": 60,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "severity": "high",
        "expected_version": 0,
    }


def test_phase6o_account_api_is_csrf_bounded_idempotent_and_tenant_isolated(monkeypatch, tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from backend.api import app as api_module

    db = tmp_path / "account.db"
    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH", str(db))
    api_module.reset_identity_runtime_for_tests(db)
    api_module.reset_alert_manager_runtime_for_tests(db)
    watchlist_id = _seed(db)
    account_a = TestClient(api_module.create_app())
    account_b = TestClient(api_module.create_app())
    csrf_a = _signin(account_a, "analyst-a")
    _signin(account_b, "analyst-b")

    assert account_a.post("/api/account/alert-manager/rules", json=_rule(watchlist_id)).status_code == 403
    poisoned = account_a.post(
        "/api/account/alert-manager/rules",
        json={**_rule(watchlist_id), "tenant_id": "other"},
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert poisoned.status_code == 422
    created = account_a.post(
        "/api/account/alert-manager/rules",
        json=_rule(watchlist_id),
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert created.status_code == 201
    rule_id = created.json()["data"]["rule"]["resource_id"]

    evaluated = account_a.post(
        "/api/account/alert-manager/evaluations",
        json={"idempotency_key": "phase6o-api-evaluate"},
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert evaluated.status_code == 201
    assert evaluated.json()["data"]["evaluation"]["triggered_count"] == 1
    assert evaluated.json()["data"]["evaluation"]["provider_call_count"] == 0

    manager = account_a.get("/api/account/alert-manager")
    assert manager.status_code == 200
    payload = manager.json()
    assert payload["payload_type"] == "watchlist_alert_manager"
    assert payload["data"]["summary"]["trigger_count"] == 1
    assert "tenant_id" not in str(payload).lower()
    assert "owner_user_id" not in str(payload).lower()
    trigger_id = payload["data"]["triggers"][0]["trigger_id"]

    assert account_b.get(f"/api/account/alert-manager/rules/{rule_id}").status_code == 404
    assert account_b.get("/api/account/alert-manager").json()["data"]["rules"] == []
    assert account_b.get(f"/api/account/alert-manager/triggers/{trigger_id}").status_code == 404

    conflict = account_a.patch(
        f"/api/account/alert-manager/rules/{rule_id}",
        json={"action": "pause", "expected_version": 99},
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert conflict.status_code == 409
    assert conflict.json()["data"]["current_version"] == 1

    reviewed = account_a.patch(
        f"/api/account/alert-manager/triggers/{trigger_id}",
        json={"action": "acknowledge", "expected_version": 1},
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["data"]["trigger"]["review_state"] == "acknowledged"
    exported = account_a.get("/api/account/alert-manager/export")
    assert exported.status_code == 200
    assert exported.json()["data"]["provider_call_count"] == 0


def test_phase6o_same_origin_proxy_allows_only_alert_manager_routes():
    root = Path(__file__).resolve().parents[1]
    proxy = (root / "apps/web/src/app/api/account/[...path]/route.ts").read_text(encoding="utf-8")

    for marker in (
        '"alert-manager"',
        '"alert-manager/evaluations"',
        '"alert-manager/export"',
        "^alert-manager\\/rules\\/[a-z0-9_]",
        "^alert-manager\\/triggers\\/[a-z0-9_]",
    ):
        assert marker in proxy
    assert "MAX_BODY_BYTES" in proxy
    assert "sameOrigin(request)" in proxy


def test_phase6o_api_contract_fixture_is_json_safe_and_honest():
    from lib.api_contracts import build_api_watchlist_alert_manager_payload, validate_api_payload
    from lib.watchlist_alert_manager import build_watchlist_alert_manager_fixture_contract

    payload = build_api_watchlist_alert_manager_payload(build_watchlist_alert_manager_fixture_contract())
    assert validate_api_payload(payload) == (True, [])
    assert payload["payload_type"] == "watchlist_alert_manager"
    assert payload["data"]["contract_version"] == "watchlist_alert_manager.v1"
    assert payload["data"]["worker"]["view_starts_worker"] is False
    assert payload["data"]["hosted_readiness"]["status"] == "unavailable"
    assert payload["summary"]["provider_call_count"] == 0
