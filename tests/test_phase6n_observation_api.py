from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


NOW = datetime(2026, 7, 13, 15, 0, tzinfo=timezone.utc)


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


def _seed_account_watchlist(db_path: Path) -> str:
    from lib.research_workspace_db import execute_query, json_dumps

    watchlist_id = "twl_phase6n_api"
    tenant_id = "tnt_local_a_8c31e2"
    user_id = "usr_local_a_2f41d0"
    timestamp = NOW.isoformat()
    execute_query(
        "INSERT INTO tenant_watchlists (resource_id, tenant_id, owner_user_id, name, source_key, source_fingerprint, version, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
        (watchlist_id, tenant_id, user_id, "API Daily", "phase6n-api", "source-fingerprint", timestamp, timestamp),
        db_path=db_path,
    )
    execute_query(
        "INSERT INTO tenant_watchlist_items (resource_id, tenant_id, watchlist_resource_id, symbol, asset_class, display_name, exchange, position, provider, source_url, source_status, observed_at, retrieved_at, evidence_json, version, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
        (
            "twi_phase6n_aapl", tenant_id, watchlist_id, "AAPL", "equity", "Apple Inc.", "NASDAQ",
            "phase6n-test", "https://finance.yahoo.com/quote/AAPL", "cached",
            "2026-07-10T20:00:00+00:00", "2026-07-10T20:05:00+00:00", json_dumps({}), timestamp, timestamp,
        ),
        db_path=db_path,
    )
    return watchlist_id


class FakeObservationAdapter:
    def __init__(self):
        self.calls = 0

    def observe(self, watchlist, plan, *, previous_rows, cancellation_requested):
        self.calls += 1
        assert cancellation_requested() is False
        symbol = watchlist["items"][0]["symbol"]
        retrieved = "2026-07-13T20:05:00+00:00"
        return {
            "rows": [
                {
                    "symbol": symbol,
                    "identity": {"symbol": symbol, "asset_class": "equity", "exchange": "NASDAQ", "identity_status": "exact"},
                    "status": "fresh",
                    "source_status": "live/fresh",
                    "observed_at": "2026-07-13T20:00:00+00:00",
                    "retrieved_at": retrieved,
                    "fetched_at": retrieved,
                    "quote": {"last_price": 210.0, "change_pct": 1.2, "market_data_as_of": "2026-07-13T20:00:00+00:00", "retrieved_at": retrieved, "provider": "test-provider", "source_url": "https://example.test/aapl", "source_status": "live/fresh"},
                    "performance": {}, "risk": {}, "technicals": {}, "financials": {}, "catalysts": {},
                    "source_register": [{"provider": "test-provider", "source_url": "https://example.test/aapl", "source_status": "live/fresh", "observed_at": "2026-07-13T20:00:00+00:00", "retrieved_at": retrieved}],
                    "confidence": 0.8, "caveat": "Controlled adapter.", "data_gap": None, "not_financial_advice": True,
                }
            ],
            "provider_budget": {"maximum_calls": 16, "actual_calls": 1, "actual_calls_by_operation": {"test:quote": 1}, "cache_hits": 0, "stale_hits": 0, "failed_calls": 0, "blocked_calls": 0, "skipped_calls": 0},
            "provider_states": [{"provider": "test-provider", "operation": "quote", "configured": True, "contacted": True, "source_status": "live/fresh"}],
            "missing_capabilities": [],
        }


def test_phase6n_account_run_api_enforces_csrf_idempotency_and_ab_isolation(monkeypatch, tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from backend.api import app as api_module

    account_db = tmp_path / "account.db"
    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH", str(account_db))
    adapter = FakeObservationAdapter()
    api_module.reset_identity_runtime_for_tests(account_db)
    api_module.reset_observation_runtime_for_tests(account_db, adapter=adapter, execute_inline=True)
    watchlist_id = _seed_account_watchlist(account_db)
    app = api_module.create_app()
    account_a = TestClient(app)
    account_b = TestClient(app)
    csrf_a = _signin(account_a, "analyst-a")
    csrf_b = _signin(account_b, "analyst-b")
    body = {
        "watchlist_id": watchlist_id,
        "idempotency_key": "phase6n-api-observation",
        "interval": "1d",
        "range": "3mo",
        "max_symbols": 5,
        "session_policy": "force-bounded",
    }

    assert account_a.post("/api/account/observation-runs", json=body).status_code == 403
    poisoned = account_a.post(
        "/api/account/observation-runs",
        json={**body, "tenant_id": "other"},
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert poisoned.status_code == 422
    started = account_a.post(
        "/api/account/observation-runs",
        json=body,
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert started.status_code in {200, 201, 202}
    payload = started.json()
    assert payload["payload_type"] == "observation_run"
    run_id = payload["data"]["run_id"]
    assert payload["data"]["status"] == "completed"
    assert "tenant_id" not in str(payload).lower()
    assert "owner_user_id" not in str(payload).lower()

    replay = account_a.post(
        "/api/account/observation-runs",
        json=body,
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert replay.json()["data"]["run_id"] == run_id
    assert adapter.calls == 1
    assert account_a.get(f"/api/account/observation-runs/{run_id}").status_code == 200
    assert account_a.get("/api/account/observation-runs").json()["data"]["runs"][0]["run_id"] == run_id
    assert account_b.get(f"/api/account/observation-runs/{run_id}").status_code == 404
    assert account_b.post(
        f"/api/account/observation-runs/{run_id}/cancel",
        json={},
        headers={"origin": "http://testserver", "x-csrf-token": csrf_b},
    ).status_code == 404


def test_phase6n_account_attention_reads_run_and_diff_without_adapter_call(monkeypatch, tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from backend.api import app as api_module

    account_db = tmp_path / "account.db"
    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "true")
    adapter = FakeObservationAdapter()
    api_module.reset_identity_runtime_for_tests(account_db)
    api_module.reset_observation_runtime_for_tests(account_db, adapter=adapter, execute_inline=True)
    watchlist_id = _seed_account_watchlist(account_db)
    client = TestClient(api_module.create_app())
    csrf = _signin(client, "analyst-a")
    response = client.post(
        "/api/account/observation-runs",
        json={"watchlist_id": watchlist_id, "idempotency_key": "phase6n-attention-read", "max_symbols": 5, "session_policy": "force-bounded"},
        headers={"origin": "http://testserver", "x-csrf-token": csrf},
    )
    assert response.status_code in {200, 201, 202}
    calls_after_run = adapter.calls

    for _ in range(3):
        attention = client.get("/api/account/attention-desk?mode=fixture")
        assert attention.status_code == 200
        data = attention.json()["data"]
        assert data["observation_run"]["latest_run"]["status"] == "completed"
        assert data["observation_run"]["provider_call_count"] == 0
    assert adapter.calls == calls_after_run


def test_phase6n_next_account_proxy_allows_only_bounded_run_routes():
    root = Path(__file__).resolve().parents[1]
    proxy = (root / "apps/web/src/app/api/account/[...path]/route.ts").read_text(encoding="utf-8")

    assert '"observation-runs"' in proxy
    assert "^observation-runs\\/[a-z0-9_]{" in proxy
    assert "observation-runs\\/[a-z0-9_]{3,80}\\/cancel" in proxy
    assert "MAX_BODY_BYTES" in proxy
    assert "sameOrigin(request)" in proxy

