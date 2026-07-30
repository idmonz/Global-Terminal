from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


class FakeService:
    def __init__(self, claim: dict, *, document: dict | None = None):
        self.claim_row = claim
        self.document = document or {"payload": {}, "version": 3}
        self.calls: list[tuple[str, object]] = []

    def claim(self, worker_id: str, *, lease_seconds: int = 120) -> dict:
        self.calls.append(("claim", {"worker_id": worker_id, "lease_seconds": lease_seconds}))
        return dict(self.claim_row)

    def heartbeat(self, claim: dict, *, lease_seconds: int = 120) -> dict:
        self.calls.append(("heartbeat", claim.get("scheduler_run_id")))
        return {"status": "running"}

    def load_account_document(self, claim: dict) -> dict:
        self.calls.append(("load", claim.get("scheduler_run_id")))
        return dict(self.document)

    def persist_account_document(self, claim: dict, bundle: dict, *, expected_version: int) -> dict:
        self.calls.append(("persist", {"expected_version": expected_version, "bundle": bundle}))
        return {"status": "applied", "version": expected_version + 1}

    def finish(self, claim: dict, result: dict) -> dict:
        self.calls.append(("finish", dict(result)))
        return {"status": result.get("status"), "idempotent_replay": False}


def _claim(**overrides: object) -> dict:
    row = {
        "claimed": True,
        "status": "leased",
        "scheduler_run_id": "hsrun_phase6q_worker",
        "schedule_id": "hsched_phase6q_worker",
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "owner_user_id": "22222222-2222-2222-2222-222222222222",
        "account_document_id": "33333333-3333-3333-3333-333333333333",
        "account_document_version": 3,
        "watchlist_id": "twl_phase6q",
        "alert_rule_id": "alrule_phase6q",
        "bounds": {"max_symbols": 1, "max_provider_calls": 4, "max_attempts": 2, "timeout_seconds": 90},
        "_lease_token": "private-lease-token",
    }
    row.update(overrides)
    return row


def test_phase6q_worker_no_due_makes_no_document_or_provider_work():
    from lib.hosted_scheduler_worker import run_hosted_scheduler_once

    service = FakeService({"claimed": False, "status": "no-due", "reason": "no-enabled-due-schedule"})
    executor_calls = 0

    def executor(claim: dict, document: dict) -> dict:
        nonlocal executor_calls
        executor_calls += 1
        return {}

    result = run_hosted_scheduler_once(service, executor=executor)
    assert result["status"] == "no-due"
    assert result["provider_call_count"] == 0
    assert result["secrets_printed"] is False
    assert executor_calls == 0
    assert [name for name, _ in service.calls] == ["claim"]


def test_phase6q_worker_success_orders_lease_document_engine_persist_and_finish():
    from lib.hosted_scheduler_worker import run_hosted_scheduler_once

    service = FakeService(_claim(), document={"payload": {"account_continuity_version": "account_continuity.v1"}, "version": 3})

    def executor(claim: dict, document: dict) -> dict:
        assert claim["_lease_token"] == "private-lease-token"
        assert document["version"] == 3
        return {
            "bundle": {"fingerprint": "a" * 64, "tables": {}, "provider_call_count": 0},
            "document_version": 3,
            "result": {
                "status": "completed",
                "provider_call_count": 1,
                "trigger_count": 1,
                "source_status": "live/fresh",
            },
        }

    result = run_hosted_scheduler_once(service, executor=executor)
    assert result["status"] == "completed"
    assert result["provider_call_count"] == 1
    assert result["trigger_count"] == 1
    assert result["document_status"] == "applied"
    assert [name for name, _ in service.calls] == ["claim", "heartbeat", "load", "persist", "finish"]
    encoded = json.dumps(result).lower()
    assert "private-lease-token" not in encoded
    assert "tenant_id" not in encoded
    assert "owner_user_id" not in encoded


def test_phase6q_worker_failure_finishes_safely_without_exception_or_secret():
    from lib.hosted_scheduler_worker import run_hosted_scheduler_once

    service = FakeService(_claim())

    def executor(claim: dict, document: dict) -> dict:
        del claim, document
        raise RuntimeError("provider body with private-lease-token")

    result = run_hosted_scheduler_once(service, executor=executor)
    assert result["status"] == "failed"
    assert result["finish_confirmed"] is True
    assert result["provider_call_count"] == 0
    assert "private-lease-token" not in json.dumps(result)
    finish = next(value for name, value in service.calls if name == "finish")
    assert finish["status"] == "failed"
    assert finish["source_status"] == "unavailable"


def test_phase6q_executor_reuses_observation_and_alert_engines(tmp_path: Path):
    from lib.account_continuity import AccountBundleStore
    from lib.hosted_scheduler_worker import execute_claim_with_existing_engines
    from lib.identity_tenancy import local_test_context
    from lib.research_workspace_db import execute_query, json_dumps
    from lib.watchlist_alert_manager import WatchlistAlertManagerStore

    now = datetime.now(timezone.utc).replace(microsecond=0)
    db = tmp_path / "account.db"
    context = local_test_context("analyst-a")
    tenant_id = context["tenant_id"]
    user_id = context["user_id"]
    watchlist_id = "twl_phase6q_engine"
    timestamp = now.isoformat()
    execute_query(
        "INSERT INTO tenant_watchlists (resource_id, tenant_id, owner_user_id, name, source_key, source_fingerprint, version, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
        (watchlist_id, tenant_id, user_id, "Phase 6Q Engine", "phase6q-engine", "phase6q-engine-fingerprint", timestamp, timestamp),
        db_path=db,
    )
    execute_query(
        "INSERT INTO tenant_watchlist_items (resource_id, tenant_id, watchlist_resource_id, symbol, asset_class, display_name, exchange, position, provider, source_url, source_status, observed_at, retrieved_at, evidence_json, version, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
        (
            "twi_phase6q_engine_btc", tenant_id, watchlist_id, "BTCUSDT", "crypto", "Bitcoin", "Binance",
            "yfinance", "https://finance.yahoo.com/quote/BTC-USD", "cached", timestamp, timestamp,
            json_dumps({"source_status": "cached"}), timestamp, timestamp,
        ),
        db_path=db,
    )
    alert_store = WatchlistAlertManagerStore(db)
    rule = alert_store.create_rule(
        context,
        {
            "watchlist_id": watchlist_id,
            "symbol": "BTCUSDT",
            "rule_type": "price_above",
            "threshold": 200,
            "threshold_unit": "USD",
            "frequency": "15m",
            "session_policy": "market-aware",
            "cooldown_minutes": 60,
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "severity": "high",
            "expected_version": 0,
        },
        now=now,
    )
    bundle = AccountBundleStore(db).capture(context)
    adapter_seen: dict[str, object] = {}

    class ControlledObservationAdapter:
        def observe(self, watchlist, plan, *, previous_rows, cancellation_requested):
            adapter_seen.update({
                "watchlist_id": watchlist.get("resource_id"),
                "requested_symbols": plan.get("requested_symbols"),
                "previous_count": len(previous_rows),
                "cancelled": cancellation_requested(),
            })
            observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            row = {
                "symbol": "BTCUSDT",
                "identity": {"symbol": "BTCUSDT", "asset_class": "crypto", "exchange": "Binance", "identity_status": "exact"},
                "status": "fresh",
                "source_status": "live/fresh",
                "observed_at": observed_at,
                "retrieved_at": observed_at,
                "fetched_at": observed_at,
                "quote": {
                    "last_price": 212.5,
                    "change_pct": 1.4,
                    "market_data_as_of": observed_at,
                    "retrieved_at": observed_at,
                    "provider": "yfinance",
                    "source_url": "https://finance.yahoo.com/quote/BTC-USD",
                    "source_status": "live/fresh",
                },
                "performance": {"return_1w_pct": 1.4},
                "risk": {"realized_volatility_1m_pct": 18.0},
                "technicals": {"rsi_14": 54.0},
                "financials": {"availability": "available", "pe_ratio": 24.0},
                "catalysts": {"earnings": [], "news": []},
                "source_register": [{"provider": "yfinance", "source_url": "https://finance.yahoo.com/quote/BTC-USD", "source_status": "live/fresh", "observed_at": observed_at, "retrieved_at": observed_at}],
                "confidence": 0.9,
                "caveat": "Controlled source-backed test observation.",
                "data_gap": "No licensed realtime tick stream.",
                "not_financial_advice": True,
            }
            return {
                "rows": [row],
                "provider_budget": {
                    "maximum_calls": 4,
                    "actual_calls": 1,
                    "actual_calls_by_operation": {"yfinance:multi-history": 1},
                    "cache_hits": 0,
                    "stale_hits": 0,
                    "failed_calls": 0,
                    "blocked_calls": 0,
                    "skipped_calls": 0,
                },
                "provider_states": [{"provider": "yfinance", "operation": "multi-history", "configured": True, "contacted": True, "source_status": "live/fresh"}],
                "missing_capabilities": [],
            }

    claim = _claim(
        tenant_id=tenant_id,
        owner_user_id=user_id,
        watchlist_id=watchlist_id,
        alert_rule_id=rule["resource_id"],
        bounds={"max_symbols": 1, "max_provider_calls": 4, "max_attempts": 2, "timeout_seconds": 90},
    )
    execution = execute_claim_with_existing_engines(
        claim,
        {"payload": bundle, "version": 3},
        observation_adapter=ControlledObservationAdapter(),
    )

    assert adapter_seen == {"watchlist_id": watchlist_id, "requested_symbols": ["BTCUSDT"], "previous_count": 0, "cancelled": False}
    assert execution["result"]["status"] == "completed", json.dumps(execution, default=str)
    assert execution["result"]["provider_call_count"] == 1
    assert execution["result"]["provider"] == "yfinance"
    assert execution["result"]["source_status"] == "live/fresh"
    assert execution["result"]["trigger_count"] == 1
    restored_tables = execution["bundle"]["tables"]
    assert len(restored_tables["tenant_observation_runs"]) == 1
    assert len(restored_tables["tenant_observation_snapshots"]) == 1
    assert len(restored_tables["tenant_watchlist_alert_evaluations"]) == 1
    assert len(restored_tables["tenant_watchlist_alert_triggers"]) == 1


class FakeResponse:
    def __init__(self, payload: object, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self.payload


class RecordingTransport:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append((method, url, dict(kwargs)))
        return self.responses.pop(0)


def test_phase6q_service_claim_hashes_worker_and_lease_proof():
    from lib.supabase_hosted_scheduler import (
        SupabaseHostedSchedulerServiceClient,
        SupabaseHostedSchedulerServiceConfig,
    )

    transport = RecordingTransport([FakeResponse({"claimed": True, "status": "leased", "scheduler_run_id": "hsrun_phase6q"})])
    client = SupabaseHostedSchedulerServiceClient(
        SupabaseHostedSchedulerServiceConfig("https://example.supabase.co", "secret-key-value-that-is-long-enough"),
        transport=transport,
    )
    claim = client.claim("worker-phase6q")
    body = transport.calls[0][2]["json"]
    assert len(body["p_worker_hash"]) == 64
    assert len(body["p_lease_token_hash"]) == 64
    assert body["p_worker_hash"] != "worker-phase6q"
    assert "_lease_token" in claim
    assert claim["_lease_token"] not in json.dumps(body)


def test_phase6q_service_headers_distinguish_new_secret_keys_from_legacy_jwts():
    from lib.supabase_hosted_scheduler import (
        SupabaseHostedSchedulerServiceClient,
        SupabaseHostedSchedulerServiceConfig,
    )

    secret_client = SupabaseHostedSchedulerServiceClient(
        SupabaseHostedSchedulerServiceConfig("https://example.supabase.co", "sb_secret_phase6q_server_only_value"),
        transport=RecordingTransport([]),
    )
    secret_headers = secret_client._headers()
    assert secret_headers["apikey"].startswith("sb_secret_")
    assert "Authorization" not in secret_headers

    legacy_client = SupabaseHostedSchedulerServiceClient(
        SupabaseHostedSchedulerServiceConfig("https://example.supabase.co", "legacy-service-role-jwt-value"),
        transport=RecordingTransport([]),
    )
    legacy_headers = legacy_client._headers()
    assert legacy_headers["Authorization"] == "Bearer legacy-service-role-jwt-value"

    local_config = SupabaseHostedSchedulerServiceConfig("http://127.0.0.1:54321", "sb_secret_local_test_value")
    assert local_config.configured is True


def test_phase6q_user_repository_uses_user_jwt_and_rejects_identity_fields():
    import pytest

    from lib.supabase_account_runtime import SupabaseAccountConfig
    from lib.supabase_hosted_scheduler import SupabaseHostedSchedulerRepository

    transport = RecordingTransport([FakeResponse({"status": "applied", "version": 1, "state": "disabled"})])
    repository = SupabaseHostedSchedulerRepository(
        SupabaseAccountConfig("https://example.supabase.co", "publishable-key-value"),
        transport=transport,
    )
    context = {"authenticated": True, "identity_provider": "supabase", "_supabase_access_token": "user-jwt"}
    schedule = {
        "schedule_id": "hsched_phase6q",
        "watchlist_id": "twl_phase6q",
        "alert_rule_id": "alrule_phase6q",
        "state": "disabled",
        "timezone": "Asia/Seoul",
        "cadence_minutes": 60,
        "bounds": {"max_symbols": 1, "max_provider_calls": 4, "max_attempts": 2, "timeout_seconds": 90},
        "version": 1,
    }
    assert repository.apply(context, schedule, expected_version=0)["status"] == "applied"
    headers = transport.calls[0][2]["headers"]
    assert headers["Authorization"] == "Bearer user-jwt"
    with pytest.raises(ValueError, match="server-derived"):
        repository.apply(context, {**schedule, "tenant_id": "other"}, expected_version=0)


def test_phase6q_migration_and_workflow_keep_service_boundary_and_safe_defaults():
    root = Path(__file__).resolve().parents[1]
    migration = (root / "supabase/migrations/20260727143000_phase6q_hosted_observation_scheduler.sql").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/phase6q-hosted-observation.yml").read_text(encoding="utf-8")

    assert "global_kill_switch boolean not null default true" in migration
    assert "operator_enabled boolean not null default false" in migration
    assert "for update skip locked" in migration.lower()
    assert "unique (tenant_id, schedule_id, due_window_at)" in migration
    assert "auth.role() <> 'service_role'" in migration
    assert "grant execute on function public.global_terminal_claim_hosted_observation_schedule" in migration
    assert "to service_role" in migration
    assert "from public, anon, authenticated" in migration
    assert "global_terminal_apply_scheduler_account_document" in migration
    assert 'cron: "17 * * * *"' in workflow
    assert "vars.GLOBAL_TERMINAL_HOSTED_SCHEDULER_OPERATOR_ENABLED == 'true'" in workflow
    assert "inputs.confirm_run == true" in workflow
    assert "type: boolean" in workflow
    assert "default: false" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "timeout-minutes: 4" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "SUPABASE_SECRET_KEY: ${{ secrets.SUPABASE_SECRET_KEY }}" in workflow
