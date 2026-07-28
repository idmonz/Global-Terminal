from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


NOW = datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)


def _seed_watchlist_and_snapshot(db_path: Path, *, price: float = 212.5, source_status: str = "live/fresh") -> tuple[dict, str, str]:
    from lib.identity_tenancy import local_test_context
    from lib.research_workspace_db import execute_query, json_dumps

    context = local_test_context("analyst-a")
    tenant_id = context["tenant_id"]
    user_id = context["user_id"]
    watchlist_id = "twl_phase6o_daily"
    run_id = "obsrun_phase6o_seed"
    timestamp = NOW.isoformat()
    execute_query(
        "INSERT INTO tenant_watchlists (resource_id, tenant_id, owner_user_id, name, source_key, source_fingerprint, version, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
        (watchlist_id, tenant_id, user_id, "Phase 6O Daily", "phase6o", "phase6o-fingerprint", timestamp, timestamp),
        db_path=db_path,
    )
    execute_query(
        "INSERT INTO tenant_watchlist_items (resource_id, tenant_id, watchlist_resource_id, symbol, asset_class, display_name, exchange, position, provider, source_url, source_status, observed_at, retrieved_at, evidence_json, version, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
        (
            "twi_phase6o_aapl", tenant_id, watchlist_id, "AAPL", "equity", "Apple Inc.", "NASDAQ",
            "test-provider", "https://example.test/aapl", source_status,
            timestamp, timestamp, json_dumps({}), timestamp, timestamp,
        ),
        db_path=db_path,
    )
    execute_query(
        "INSERT INTO tenant_observation_runs (run_id, tenant_id, owner_user_id, watchlist_resource_id, watchlist_name, idempotency_key, request_fingerprint, status, interval, range_name, max_symbols, requested_symbols_json, requested_count, completed_count, provider_call_budget, provider_call_count, session_json, provider_plan_json, provider_states_json, missing_capabilities_json, diff_json, attempted_at, started_at, observation_started_at, observation_ended_at, retrieved_at, completed_at, duration_ms, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', '1d', '3mo', 5, ?, 1, 1, 16, 1, '{}', '{}', '[]', '[]', ?, ?, ?, ?, ?, ?, ?, 10, 1, ?, ?)",
        (
            run_id, tenant_id, user_id, watchlist_id, "Phase 6O Daily", "phase6o-seed-run", "phase6o-run-fingerprint",
            json_dumps(["AAPL"]), json_dumps({"material_change_count": 1, "symbols": ["AAPL"]}),
            timestamp, timestamp, timestamp, timestamp, timestamp, timestamp, timestamp, timestamp,
        ),
        db_path=db_path,
    )
    payload = {
        "symbol": "AAPL",
        "quote": {"last_price": price, "change_pct": 2.4, "provider": "test-provider", "source_status": source_status},
        "source_register": [{"provider": "test-provider", "source_url": "https://example.test/aapl", "source_status": source_status}],
        "confidence": 0.9,
        "caveat": "Controlled delayed observation.",
        "data_gap": "No licensed real-time tick stream.",
    }
    execute_query(
        "INSERT INTO tenant_observation_snapshots (snapshot_id, tenant_id, owner_user_id, run_id, watchlist_resource_id, symbol, asset_class, snapshot_status, source_status, observed_at, retrieved_at, provider, source_url, confidence, content_hash, payload_json, caveat, data_gap, created_at) VALUES (?, ?, ?, ?, ?, 'AAPL', 'equity', ?, ?, ?, ?, 'test-provider', 'https://example.test/aapl', 0.9, ?, ?, ?, ?, ?)",
        (
            "obssnap_phase6o_aapl", tenant_id, user_id, run_id, watchlist_id,
            "fresh" if source_status == "live/fresh" else "stale", source_status, timestamp, timestamp,
            f"hash-{price}-{source_status}", json_dumps(payload), payload["caveat"], payload["data_gap"], timestamp,
        ),
        db_path=db_path,
    )
    return context, watchlist_id, run_id


def _rule_body(watchlist_id: str, **overrides) -> dict:
    body = {
        "watchlist_id": watchlist_id,
        "symbol": "AAPL",
        "rule_type": "price_above",
        "threshold": 200,
        "threshold_unit": "USD",
        "frequency": "15m",
        "session_policy": "market-aware",
        "cooldown_minutes": 60,
        "expires_at": (NOW + timedelta(days=7)).isoformat(),
        "severity": "high",
        "expected_version": 0,
    }
    body.update(overrides)
    return body


def test_phase6o_rule_validation_is_bounded_and_rejects_identity_fields():
    from lib.watchlist_alert_manager import validate_alert_rule_request

    result = validate_alert_rule_request(_rule_body("twl_daily"), now=NOW)
    assert result["metric"] == "last_price"
    assert result["operator"] == "above"
    assert result["frequency_minutes"] == 15
    assert result["delivery"] == "in-app-only"

    for poisoned in ({"tenant_id": "other"}, {"owner_user_id": "other"}, {"webhook": "https://example.test"}):
        with pytest.raises(ValueError):
            validate_alert_rule_request({**_rule_body("twl_daily"), **poisoned}, now=NOW)
    with pytest.raises(ValueError):
        validate_alert_rule_request(_rule_body("twl_daily", threshold=float("nan")), now=NOW)


def test_phase6o_create_due_evaluate_trigger_and_cooldown_are_tenant_safe(tmp_path: Path):
    from lib.identity_tenancy import local_test_context
    from lib.watchlist_alert_manager import AlertManagerConflict, WatchlistAlertManagerStore

    db = tmp_path / "account.db"
    account_a, watchlist_id, _ = _seed_watchlist_and_snapshot(db)
    account_b = local_test_context("analyst-b")
    store = WatchlistAlertManagerStore(db)
    rule = store.create_rule(account_a, _rule_body(watchlist_id), now=NOW)

    assert rule["state"] == "active"
    assert rule["next_due_at"] == NOW.isoformat()
    assert store.list_rules(account_b) == []
    assert store.get_rule(account_b, rule["resource_id"]) is None

    run = store.evaluate_due(account_a, {"idempotency_key": "phase6o-evaluate-001"}, now=NOW)
    assert run["status"] == "completed"
    assert run["provider_call_count"] == 0
    assert run["evaluated_count"] == 1
    assert run["triggered_count"] == 1
    assert run["source_clock"]["observed_at"] == NOW.isoformat()
    triggers = store.list_triggers(account_a)
    assert len(triggers) == 1
    assert triggers[0]["evidence"]["snapshot_id"] == "obssnap_phase6o_aapl"
    assert triggers[0]["clocks"]["reviewed_at"] is None
    assert store.list_triggers(account_b) == []

    replay = store.evaluate_due(account_a, {"idempotency_key": "phase6o-evaluate-001"}, now=NOW)
    assert replay["run_id"] == run["run_id"]
    assert replay["idempotent_replay"] is True
    assert len(store.list_triggers(account_a)) == 1

    not_due = store.evaluate_due(account_a, {"idempotency_key": "phase6o-evaluate-002"}, now=NOW + timedelta(minutes=5))
    assert not_due["due_count"] == 0
    assert len(store.list_triggers(account_a)) == 1

    with pytest.raises(AlertManagerConflict):
        store.update_rule(account_a, rule["resource_id"], {"action": "pause", "expected_version": 99}, now=NOW)


def test_phase6o_stale_price_is_gap_but_source_degradation_can_trigger(tmp_path: Path):
    from lib.watchlist_alert_manager import WatchlistAlertManagerStore

    db = tmp_path / "account.db"
    context, watchlist_id, _ = _seed_watchlist_and_snapshot(db, price=250, source_status="stale")
    store = WatchlistAlertManagerStore(db)
    price_rule = store.create_rule(context, _rule_body(watchlist_id), now=NOW)
    degradation = store.create_rule(
        context,
        _rule_body(
            watchlist_id,
            rule_type="source_degradation",
            threshold="stale",
            threshold_unit="status",
            expected_version=0,
        ),
        now=NOW,
    )

    run = store.evaluate_due(context, {"idempotency_key": "phase6o-stale-eval"}, now=NOW)
    assert run["evaluated_count"] == 2
    assert run["triggered_count"] == 1
    assert run["data_gap_count"] == 1
    triggers = store.list_triggers(context)
    assert triggers[0]["rule_id"] == degradation["resource_id"]
    assert triggers[0]["source_status"] == "stale"
    assert triggers[0]["live_intelligence_claimed"] is False
    assert all(row["rule_id"] != price_rule["resource_id"] for row in triggers)


def test_phase6o_lifecycle_worker_truth_review_export_and_delete(tmp_path: Path, monkeypatch):
    from lib.watchlist_alert_manager import WatchlistAlertManagerStore, build_alert_worker_status

    db = tmp_path / "account.db"
    context, watchlist_id, _ = _seed_watchlist_and_snapshot(db)
    store = WatchlistAlertManagerStore(db)
    rule = store.create_rule(context, _rule_body(watchlist_id), now=NOW)
    paused = store.update_rule(context, rule["resource_id"], {"action": "pause", "expected_version": 1}, now=NOW)
    assert paused["state"] == "paused"
    resumed = store.update_rule(context, rule["resource_id"], {"action": "resume", "expected_version": 2}, now=NOW)
    assert resumed["state"] == "active"

    run = store.evaluate_due(context, {"idempotency_key": "phase6o-review-eval"}, now=NOW)
    trigger = store.list_triggers(context)[0]
    reviewed = store.review_trigger(context, trigger["trigger_id"], {"action": "acknowledge", "expected_version": 1}, now=NOW)
    assert reviewed["review_state"] == "acknowledged"
    assert reviewed["clocks"]["reviewed_at"] == NOW.isoformat()

    monkeypatch.delenv("GLOBAL_TERMINAL_ALERT_WORKER_ENABLED", raising=False)
    status = build_alert_worker_status(store, context, now=NOW)
    assert status["enabled"] is False
    assert status["state"] == "stopped"
    assert status["view_starts_worker"] is False

    exported = store.export_manager(context)
    assert exported["provider_call_count"] == 0
    assert "tenant_id" not in str(exported).lower()
    assert store.delete_rule(context, rule["resource_id"], expected_version=3, now=NOW) is True
    assert store.get_rule(context, rule["resource_id"])["state"] == "deleted"
    assert run["provider_call_count"] == 0


def test_phase6o_manager_contract_has_required_states_and_distinct_clocks(tmp_path: Path):
    from lib.watchlist_alert_manager import WatchlistAlertManagerStore, build_watchlist_alert_manager_contract

    db = tmp_path / "account.db"
    context, watchlist_id, _ = _seed_watchlist_and_snapshot(db)
    store = WatchlistAlertManagerStore(db)
    store.create_rule(context, _rule_body(watchlist_id), now=NOW)
    store.evaluate_due(context, {"idempotency_key": "phase6o-contract-eval"}, now=NOW)
    contract = build_watchlist_alert_manager_contract(context, store=store, now=NOW)

    assert contract["contract_version"] == "watchlist_alert_manager.v1"
    assert contract["summary"]["provider_call_count"] == 0
    assert contract["worker"]["view_starts_worker"] is False
    assert contract["hosted_readiness"]["status"] == "unavailable"
    assert contract["delivery_channels"]["in_app"] == "available"
    assert contract["delivery_channels"]["email"] == "unavailable"
    assert {"observation", "retrieval", "evaluation", "trigger", "review"} <= set(contract["clock_legend"])
    assert contract["rules"][0]["schedule"]["frequency"] == "15m"
    assert contract["triggers"][0]["evidence_links"][0]["href"].startswith("/?view=analyst-workspace")


def test_phase6o_cooldown_is_proven_at_the_next_due_window(tmp_path: Path):
    from lib.watchlist_alert_manager import WatchlistAlertManagerStore

    db = tmp_path / "cooldown.db"
    context, watchlist_id, _ = _seed_watchlist_and_snapshot(db)
    store = WatchlistAlertManagerStore(db)
    rule = store.create_rule(context, _rule_body(watchlist_id), now=NOW)
    first = store.evaluate_due(context, {"idempotency_key": "phase6o-cooldown-first"}, now=NOW)
    second = store.evaluate_due(context, {"idempotency_key": "phase6o-cooldown-next"}, now=NOW + timedelta(minutes=15))

    assert first["triggered_count"] == 1
    assert second["due_count"] == 1
    assert second["triggered_count"] == 0
    assert second["deduped_count"] == 1
    assert len(store.list_triggers(context)) == 1
    assert store.get_rule(context, rule["resource_id"])["last_triggered_at"] == NOW.isoformat()


def test_phase6o_quota_block_and_provider_gap_are_distinct_real_states(tmp_path: Path):
    from lib.research_workspace_db import execute_query, json_dumps
    from lib.watchlist_alert_manager import WatchlistAlertManagerStore

    quota_db = tmp_path / "quota.db"
    quota_context, quota_watchlist, quota_run = _seed_watchlist_and_snapshot(quota_db)
    execute_query("DELETE FROM tenant_observation_snapshots", db_path=quota_db)
    execute_query(
        "UPDATE tenant_observation_runs SET status='partial', missing_capabilities_json=? WHERE run_id=?",
        (json_dumps([{"provider": "alpha-vantage", "reason": "daily-quota-exhausted"}]), quota_run),
        db_path=quota_db,
    )
    quota_store = WatchlistAlertManagerStore(quota_db)
    quota_store.create_rule(quota_context, _rule_body(quota_watchlist), now=NOW)
    quota_result = quota_store.evaluate_due(quota_context, {"idempotency_key": "phase6o-quota-blocked"}, now=NOW)
    assert quota_result["status"] == "quota-blocked"
    assert quota_result["quota_blocked_count"] == 1
    assert quota_result["data_gap_count"] == 0
    assert quota_result["provider_call_count"] == 0

    provider_db = tmp_path / "provider.db"
    provider_context, provider_watchlist, provider_run = _seed_watchlist_and_snapshot(provider_db)
    execute_query("DELETE FROM tenant_observation_snapshots", db_path=provider_db)
    execute_query(
        "UPDATE tenant_observation_runs SET status='failed', missing_capabilities_json=?, error_code='provider-unavailable' WHERE run_id=?",
        (json_dumps([{"provider": "test-provider", "reason": "provider-unavailable"}]), provider_run),
        db_path=provider_db,
    )
    provider_store = WatchlistAlertManagerStore(provider_db)
    provider_store.create_rule(provider_context, _rule_body(provider_watchlist), now=NOW)
    provider_result = provider_store.evaluate_due(provider_context, {"idempotency_key": "phase6o-provider-gap"}, now=NOW)
    assert provider_result["status"] == "partial"
    assert provider_result["quota_blocked_count"] == 0
    assert provider_result["data_gap_count"] == 1
    assert provider_result["provider_call_count"] == 0


def test_phase6o_no_rules_expiry_cancel_and_worker_restart_are_observable(tmp_path: Path, monkeypatch):
    from lib.watchlist_alert_manager import (
        WatchlistAlertManagerStore,
        build_alert_worker_status,
        build_watchlist_alert_manager_contract,
        run_alert_worker_once,
    )

    db = tmp_path / "worker.db"
    context, watchlist_id, _ = _seed_watchlist_and_snapshot(db)
    store = WatchlistAlertManagerStore(db)
    empty = build_watchlist_alert_manager_contract(context, store=store, now=NOW)
    assert empty["summary"]["rule_count"] == 0
    assert empty["summary"]["due_count"] == 0

    expiring = store.create_rule(
        context,
        _rule_body(watchlist_id, expires_at=(NOW + timedelta(minutes=1)).isoformat()),
        now=NOW,
    )
    plan = store.plan_due(context, now=NOW + timedelta(minutes=2))
    assert store.get_rule(context, expiring["resource_id"])["state"] == "expired"
    assert plan["due_count"] == 0

    cancellable = store.create_rule(
        context,
        _rule_body(watchlist_id, rule_type="price_below", threshold=100),
        now=NOW + timedelta(minutes=2),
    )
    cancelled = store.update_rule(
        context,
        cancellable["resource_id"],
        {"action": "cancel", "expected_version": 1},
        now=NOW + timedelta(minutes=2),
    )
    assert cancelled["state"] == "cancelled"

    monkeypatch.setenv("GLOBAL_TERMINAL_ALERT_WORKER_ENABLED", "true")
    assert build_alert_worker_status(store, context, now=NOW + timedelta(minutes=2))["state"] == "offline"
    store.mark_worker_state(context, "offline", error_code="simulated-offline", now=NOW + timedelta(minutes=2))
    result = run_alert_worker_once(context, store=store, now=NOW + timedelta(minutes=3))
    worker = build_alert_worker_status(store, context, now=NOW + timedelta(minutes=3))
    assert result["provider_call_count"] == 0
    assert worker["state"] == "idle"
    assert worker["restart_count"] == 1
    assert worker["view_starts_worker"] is False
    assert worker["observation_jobs_enabled"] is False
