from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


NOW = datetime(2026, 7, 27, 6, 17, 42, tzinfo=timezone.utc)


def _seed_parents(db_path: Path, label: str = "analyst-a") -> tuple[dict, str, str]:
    from lib.identity_tenancy import local_test_context
    from lib.research_workspace_db import execute_query, json_dumps

    context = local_test_context(label)
    tenant_id = context["tenant_id"]
    user_id = context["user_id"]
    suffix = label.replace("-", "_")
    watchlist_id = f"twl_phase6q_{suffix}"
    rule_id = f"alrule_phase6q_{suffix}"
    timestamp = NOW.isoformat()
    execute_query(
        "INSERT INTO tenant_watchlists (resource_id, tenant_id, owner_user_id, name, source_key, source_fingerprint, version, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
        (watchlist_id, tenant_id, user_id, "Phase 6Q Pilot", "phase6q", f"phase6q-{suffix}", timestamp, timestamp),
        db_path=db_path,
    )
    execute_query(
        "INSERT INTO tenant_watchlist_items (resource_id, tenant_id, watchlist_resource_id, symbol, asset_class, display_name, exchange, position, provider, source_url, source_status, observed_at, retrieved_at, evidence_json, version, active, created_at, updated_at) VALUES (?, ?, ?, 'AAPL', 'equity', 'Apple Inc.', 'NASDAQ', 0, 'test-provider', 'https://example.test/aapl', 'live/fresh', ?, ?, ?, 1, 1, ?, ?)",
        (f"twi_phase6q_{suffix}", tenant_id, watchlist_id, timestamp, timestamp, json_dumps({}), timestamp, timestamp),
        db_path=db_path,
    )
    execute_query(
        """
        INSERT INTO tenant_watchlist_alert_rules (
            resource_id, tenant_id, owner_user_id, watchlist_resource_id,
            symbol, asset_class, rule_type, metric, operator, threshold_json,
            threshold_unit, frequency, frequency_minutes, session_policy,
            cooldown_minutes, severity, state, fingerprint, next_due_at,
            expires_at, version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'AAPL', 'equity', 'price_above', 'last_price',
                  'above', '200', 'USD', '1h', 60, 'market-aware', 60,
                  'high', 'active', ?, ?, ?, 1, ?, ?)
        """,
        (
            rule_id,
            tenant_id,
            user_id,
            watchlist_id,
            f"phase6q-rule-{suffix}",
            timestamp,
            (NOW + timedelta(days=7)).isoformat(),
            timestamp,
            timestamp,
        ),
        db_path=db_path,
    )
    return context, watchlist_id, rule_id


def _schedule_body(watchlist_id: str, rule_id: str, **overrides: object) -> dict:
    body = {
        "watchlist_id": watchlist_id,
        "alert_rule_id": rule_id,
        "timezone": "Asia/Seoul",
        "cadence_minutes": 60,
        "max_symbols": 1,
        "max_provider_calls": 4,
        "max_attempts": 2,
        "timeout_seconds": 90,
    }
    body.update(overrides)
    return body


def _completed_result(**overrides: object) -> dict:
    result = {
        "status": "completed",
        "observation_run_id": "obsrun_phase6q_source_backed",
        "evaluation_run_id": "alertrun_phase6q_source_backed",
        "trigger_count": 1,
        "provider_call_count": 1,
        "provider": "yfinance",
        "source_url": "https://finance.yahoo.com/quote/AAPL",
        "source_status": "live/fresh",
        "observed_at": (NOW - timedelta(minutes=5)).isoformat(),
        "retrieved_at": NOW.isoformat(),
        "evaluated_at": NOW.isoformat(),
        "triggered_at": NOW.isoformat(),
        "duration_ms": 12_000,
        "caveat": "Public delayed source; no licensed realtime tick stream.",
        "data_gap": "Hosted deployment is not proven by this local test.",
    }
    result.update(overrides)
    return result


def _hosted_evidence(**overrides: object) -> dict:
    from lib.hosted_scheduler_operations import HOSTED_EVIDENCE_ASSERTIONS

    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    evidence = {
        "evidence_version": "phase6q.hosted.handoff.v1",
        "captured_at": captured_at,
        "passed": True,
        "hosted_scheduler_verified": True,
        "runner": {
            "kind": "github-actions-python",
            "deployed": True,
            "default_branch_workflow": True,
            "invocation_observed": True,
            "job_history_observed": True,
            "concurrency_limit": 1,
            "deadline_seconds": 240,
            "workflow_version": "phase6q-worker-v1",
        },
        "assertions": {field: True for field in HOSTED_EVIDENCE_ASSERTIONS},
        "counts": {
            "page_read_provider_calls": 0,
            "overlap_additional_provider_calls": 0,
            "duplicate_runs": 0,
            "duplicate_evaluations": 0,
            "duplicate_triggers": 0,
            "duplicate_audit_effects": 0,
            "cross_tenant_visible_rows": 0,
            "cross_tenant_mutable_rows": 0,
            "cleanup_remaining_temp_rows": 0,
            "source_backed_results": 1,
            "provider_calls": 1,
            "trigger_count": 1,
            "job_history_rows": 1,
        },
        "source": {
            "source_backed": True,
            "provider": "yfinance",
            "source_url": "https://finance.yahoo.com/quote/AAPL",
            "source_status": "delayed/fresh",
            "retrieved_at": captured_at,
            "observed_at": captured_at,
        },
        "final_schedule_state": "disabled",
        "privacy": {
            "identifiers_redacted": True,
            "secrets_printed": False,
            "private_payloads_printed": False,
        },
    }
    evidence.update(overrides)
    return evidence


def test_phase6q_schedule_validation_due_windows_and_dst_are_bounded():
    from lib.hosted_scheduler_operations import (
        calculate_next_due,
        due_window_idempotency_key,
        normalize_timezone,
        validate_schedule_request,
    )

    validated = validate_schedule_request(_schedule_body("twl_phase6q", "alrule_phase6q"))
    assert validated["timezone"] == "Asia/Seoul"
    assert validated["max_provider_calls"] == 4
    assert normalize_timezone("America/New_York") == "America/New_York"

    anchor = datetime(2026, 10, 31, 13, 30, tzinfo=timezone.utc)  # 09:30 EDT
    after = datetime(2026, 11, 1, 13, 31, tzinfo=timezone.utc)
    next_due = calculate_next_due(after, 1_440, anchor=anchor, timezone_name="America/New_York")
    assert next_due == datetime(2026, 11, 1, 14, 30, tzinfo=timezone.utc)  # 09:30 EST
    assert due_window_idempotency_key("schedule_phase6q", next_due) == due_window_idempotency_key("schedule_phase6q", next_due)

    for poisoned in ({"tenant_id": "other"}, {"lease_token": "forged"}, {"webhook": "https://example.test"}):
        with pytest.raises(ValueError):
            validate_schedule_request({**_schedule_body("twl_phase6q", "alrule_phase6q"), **poisoned})
    with pytest.raises(ValueError):
        validate_schedule_request(_schedule_body("twl_phase6q", "alrule_phase6q", max_symbols=6))
    with pytest.raises(ValueError):
        normalize_timezone("Mars/Olympus")


def test_phase6q_schedule_crud_is_tenant_safe_and_optimistic(tmp_path: Path):
    from lib.hosted_scheduler_operations import HostedSchedulerConflict, HostedSchedulerStore
    from lib.identity_tenancy import local_test_context

    db = tmp_path / "phase6q.db"
    account_a, watchlist_id, rule_id = _seed_parents(db)
    account_b = local_test_context("analyst-b")
    store = HostedSchedulerStore(db)

    schedule = store.create_schedule(account_a, _schedule_body(watchlist_id, rule_id), now=NOW)
    assert schedule["state"] == "disabled"
    assert schedule["next_due_at"] is None
    assert store.list_schedules(account_b) == []
    assert store.get_schedule(account_b, schedule["schedule_id"]) is None
    with pytest.raises(ValueError, match="consent"):
        store.update_schedule(account_a, schedule["schedule_id"], {"action": "enable", "expected_version": 1}, now=NOW)

    enabled = store.update_schedule(
        account_a,
        schedule["schedule_id"],
        {"action": "enable", "expected_version": 1, "consent": True},
        now=NOW,
    )
    assert enabled["state"] == "enabled"
    assert enabled["next_due_at"] == NOW.isoformat()
    assert enabled["next_due_local"].endswith("+09:00")
    with pytest.raises(HostedSchedulerConflict) as conflict:
        store.update_schedule(account_a, schedule["schedule_id"], {"action": "pause", "expected_version": 1}, now=NOW)
    assert conflict.value.current_version == 2

    paused = store.update_schedule(account_a, schedule["schedule_id"], {"action": "pause", "expected_version": 2}, now=NOW)
    resumed = store.update_schedule(account_a, schedule["schedule_id"], {"action": "resume", "expected_version": 3}, now=NOW)
    assert paused["state"] == "paused"
    assert resumed["state"] == "enabled"
    assert {row["event_type"] for row in store.list_audit(account_a)} >= {
        "schedule-created",
        "schedule-enable",
        "schedule-pause",
        "schedule-resume",
    }


def test_phase6q_claim_overlap_completion_replay_quota_and_lkg(tmp_path: Path):
    from lib.hosted_scheduler_operations import HostedSchedulerStore
    from lib.identity_tenancy import local_test_context
    from lib.research_workspace_db import execute_query

    db = tmp_path / "phase6q.db"
    account_a, watchlist_id, rule_id = _seed_parents(db)
    account_b = local_test_context("analyst-b")
    store = HostedSchedulerStore(db)
    schedule = store.create_schedule(account_a, _schedule_body(watchlist_id, rule_id), now=NOW)
    schedule = store.update_schedule(account_a, schedule["schedule_id"], {"action": "enable", "expected_version": 1, "consent": True}, now=NOW)

    assert store.claim_due("worker-phase6q", now=NOW)["status"] == "disabled"
    assert store.claim_due("worker-phase6q", now=NOW, operator_enabled=True)["status"] == "killed"
    claim = store.claim_due("worker-phase6q", now=NOW, operator_enabled=True, global_kill=False)
    assert claim["claimed"] is True
    assert claim["provider_call_count"] == 0
    overlap = store.claim_due("worker-other", now=NOW + timedelta(seconds=10), operator_enabled=True, global_kill=False)
    assert overlap == {"claimed": False, "status": "overlap", "reason": "lease-active", "provider_call_count": 0}

    running = store.mark_running(claim, now=NOW + timedelta(seconds=15))
    assert running["status"] == "running"
    completed = store.finish_run(claim, _completed_result(), now=NOW + timedelta(seconds=30))
    assert completed["status"] == "completed"
    assert completed["quota"] == {"budget": 4, "used": 1, "remaining": 3}
    replay = store.finish_run(claim, _completed_result(), now=NOW + timedelta(seconds=31))
    assert replay["idempotent_replay"] is True
    assert len(store.list_runs(account_a)) == 1
    assert store.list_runs(account_b) == []

    first_run_id = completed["scheduler_run_id"]
    next_window = NOW + timedelta(hours=1)
    execute_query(
        "UPDATE tenant_hosted_observation_schedules SET next_due_at=? WHERE schedule_id=?",
        (next_window.isoformat(), schedule["schedule_id"]),
        db_path=db,
    )
    second = store.claim_due("worker-phase6q", now=next_window, operator_enabled=True, global_kill=False)
    store.mark_running(second, now=next_window + timedelta(seconds=1))
    with pytest.raises(ValueError, match="exceeds"):
        store.finish_run(second, _completed_result(provider_call_count=5), now=next_window + timedelta(seconds=2))
    degraded = store.finish_run(
        second,
        _completed_result(
            status="provider-unavailable",
            provider_call_count=0,
            source_status="unavailable",
            trigger_count=0,
            error_code="provider-timeout",
        ),
        now=next_window + timedelta(seconds=3),
    )
    assert degraded["status"] == "provider-unavailable"
    contract = store.build_contract(account_a, now=next_window + timedelta(seconds=4))
    assert contract["last_known_good"]["scheduler_run_id"] == first_run_id
    assert contract["summary"]["provider_call_count"] == 0
    assert contract["readiness"]["hosted_scheduler_verified"] is False


def test_phase6q_expired_lease_recovery_and_attempt_exhaustion(tmp_path: Path):
    from lib.hosted_scheduler_operations import HostedSchedulerLeaseError, HostedSchedulerStore

    db = tmp_path / "phase6q.db"
    context, watchlist_id, rule_id = _seed_parents(db)
    store = HostedSchedulerStore(db)
    schedule = store.create_schedule(context, _schedule_body(watchlist_id, rule_id, max_attempts=2), now=NOW)
    store.update_schedule(context, schedule["schedule_id"], {"action": "enable", "expected_version": 1, "consent": True}, now=NOW)

    first = store.claim_due("worker-phase6q-a", now=NOW, operator_enabled=True, global_kill=False, lease_seconds=30)
    recovered = store.claim_due("worker-phase6q-b", now=NOW + timedelta(seconds=31), operator_enabled=True, global_kill=False, lease_seconds=30)
    assert recovered["claimed"] is True
    assert recovered["scheduler_run_id"] == first["scheduler_run_id"]
    assert recovered["attempt_count"] == 2
    with pytest.raises(HostedSchedulerLeaseError):
        store.mark_running(first, now=NOW + timedelta(seconds=32))

    exhausted = store.claim_due("worker-phase6q-c", now=NOW + timedelta(seconds=62), operator_enabled=True, global_kill=False, lease_seconds=30)
    assert exhausted["status"] == "failed"
    assert exhausted["reason"] == "lease-attempts-exhausted"
    rows = store.list_runs(context)
    assert rows[0]["status"] == "failed"
    assert rows[0]["error_code"] == "lease-attempts-exhausted"


def test_phase6q_tenant_kill_forces_terminal_killed_and_evidence_is_strict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from lib.hosted_scheduler_operations import HostedSchedulerStore, hosted_scheduler_evidence_verified

    db = tmp_path / "phase6q.db"
    context, watchlist_id, rule_id = _seed_parents(db)
    store = HostedSchedulerStore(db)
    schedule = store.create_schedule(context, _schedule_body(watchlist_id, rule_id), now=NOW)
    enabled = store.update_schedule(context, schedule["schedule_id"], {"action": "enable", "expected_version": 1, "consent": True}, now=NOW)
    claim = store.claim_due("worker-phase6q", now=NOW, operator_enabled=True, global_kill=False)
    store.mark_running(claim, now=NOW + timedelta(seconds=1))
    killed = store.update_schedule(context, schedule["schedule_id"], {"action": "kill", "expected_version": enabled["version"]}, now=NOW + timedelta(seconds=2))
    assert killed["state"] == "killed"
    final = store.finish_run(claim, _completed_result(), now=NOW + timedelta(seconds=3))
    assert final["status"] == "killed"

    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"evidence_version": "phase6q.hosted.handoff.v1", "passed": True, "hosted_scheduler_verified": True}), encoding="utf-8")
    monkeypatch.setenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_EVIDENCE_PATH", str(evidence))
    monkeypatch.delenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_VERIFIED", raising=False)
    assert hosted_scheduler_evidence_verified() is False
    monkeypatch.setenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_VERIFIED", "true")
    assert hosted_scheduler_evidence_verified() is False
    evidence.write_text(json.dumps(_hosted_evidence()), encoding="utf-8")
    assert hosted_scheduler_evidence_verified() is True

    contract = store.build_contract(context, now=NOW)
    assert contract["readiness"]["hosted_scheduler_verified"] is True
    encoded = json.dumps(contract).lower()
    assert "lease_token" not in encoded
    assert "tenant_id" not in encoded
    assert "owner_user_id" not in encoded


def test_phase6q_hosted_evidence_verifier_rejects_private_or_incomplete_proof():
    from lib.hosted_scheduler_operations import validate_hosted_scheduler_evidence

    valid = _hosted_evidence()
    verdict = validate_hosted_scheduler_evidence(valid)
    assert verdict["passed"] is True
    assert verdict["checked_assertion_count"] == 15

    incomplete = _hosted_evidence(assertions={"deployed_invocation": True})
    assert validate_hosted_scheduler_evidence(incomplete)["passed"] is False

    private = _hosted_evidence(operator={"email": "analyst@example.test"})
    private_verdict = validate_hosted_scheduler_evidence(private)
    assert private_verdict["passed"] is False
    assert {"private-key-present", "private-value-pattern-present"} <= set(private_verdict["reasons"])


def _signin(client: object, alias: str) -> str:
    response = client.post(  # type: ignore[attr-defined]
        "/api/account/local-session",
        headers={"origin": "http://testserver"},
        json={"alias": alias, "return_to": "/?view=alert-manager"},
    )
    assert response.status_code == 201
    csrf = client.cookies.get("gt_csrf")  # type: ignore[attr-defined]
    assert csrf
    return str(csrf)


def test_phase6q_account_api_is_csrf_bounded_and_tenant_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from backend.api import app as api_module

    db = tmp_path / "phase6q-api.db"
    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH", str(db))
    monkeypatch.setenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_KILL_SWITCH", "true")
    api_module.reset_identity_runtime_for_tests(db)
    context, watchlist_id, rule_id = _seed_parents(db)
    del context
    account_a = TestClient(api_module.create_app())
    account_b = TestClient(api_module.create_app())
    csrf_a = _signin(account_a, "analyst-a")
    _signin(account_b, "analyst-b")

    route = "/api/account/alert-manager/scheduler/schedules"
    assert account_a.post(route, json=_schedule_body(watchlist_id, rule_id)).status_code == 403
    created = account_a.post(
        route,
        json=_schedule_body(watchlist_id, rule_id),
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["payload_type"] == "hosted_scheduler_schedule"
    assert payload["data"]["schedule"]["state"] == "disabled"
    schedule_id = payload["data"]["schedule"]["schedule_id"]
    assert "tenant_id" not in json.dumps(payload).lower()
    assert "lease_token" not in json.dumps(payload).lower()

    account_b_contract = account_b.get("/api/account/alert-manager/scheduler").json()
    assert account_b_contract["data"]["schedules"] == []
    assert account_b_contract["data"]["readiness"]["hosted_scheduler_verified"] is False

    no_consent = account_a.patch(
        f"{route}/{schedule_id}",
        json={"action": "enable", "expected_version": 1},
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert no_consent.status_code == 422
    enabled = account_a.patch(
        f"{route}/{schedule_id}",
        json={"action": "enable", "expected_version": 1, "consent": True},
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert enabled.status_code == 200
    assert enabled.json()["data"]["schedule"]["state"] == "enabled"
    assert enabled.json()["data"]["readiness"]["status"] == "disabled"
    conflict = account_a.patch(
        f"{route}/{schedule_id}",
        json={"action": "pause", "expected_version": 1},
        headers={"origin": "http://testserver", "x-csrf-token": csrf_a},
    )
    assert conflict.status_code == 409
    assert conflict.json()["data"]["current_version"] == 2
    audit = account_a.get("/api/account/alert-manager/scheduler/audit")
    assert audit.status_code == 200
    assert audit.json()["summary"]["provider_call_count"] == 0


def test_phase6q_account_continuity_captures_and_restores_scheduler_state(tmp_path: Path):
    from lib.account_continuity import AccountBundleStore
    from lib.hosted_scheduler_operations import HostedSchedulerStore
    from lib.research_workspace_db import execute_query

    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    context, watchlist_id, rule_id = _seed_parents(source_db)
    store = HostedSchedulerStore(source_db)
    schedule = store.create_schedule(context, _schedule_body(watchlist_id, rule_id), now=NOW)
    store.update_schedule(context, schedule["schedule_id"], {"action": "enable", "expected_version": 1, "consent": True}, now=NOW)
    claim = store.claim_due("worker-phase6q", now=NOW, operator_enabled=True, global_kill=False)
    store.mark_running(claim, now=NOW + timedelta(seconds=1))
    store.finish_run(claim, _completed_result(), now=NOW + timedelta(seconds=2))

    bundle = AccountBundleStore(source_db).capture(context)
    assert bundle["tables"]["tenant_hosted_observation_schedules"]
    assert bundle["tables"]["tenant_hosted_observation_schedule_runs"]
    assert bundle["tables"]["tenant_hosted_observation_schedule_audit"]
    encoded = json.dumps(bundle).lower()
    assert "lease_token" not in encoded
    assert "tenant_id" not in encoded
    assert "owner_user_id" not in encoded

    restored = AccountBundleStore(target_db).restore(context, bundle, prefer_remote=True)
    assert restored["status"] == "restored"
    rows = HostedSchedulerStore(target_db).list_runs(context)
    assert len(rows) == 1
    assert rows[0]["status"] == "completed"
    assert rows[0]["source"]["provider"] == "yfinance"
    assert execute_query(
        "SELECT COUNT(*) AS count FROM tenant_hosted_observation_schedule_audit",
        fetch=True,
        one=True,
        db_path=target_db,
    )["count"] >= 3
