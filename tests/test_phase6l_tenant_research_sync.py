from __future__ import annotations

import json
from pathlib import Path

import pytest


def _resource(
    resource_id: str,
    *,
    version: int = 1,
    name: str = "Daily Radar",
    deleted: bool = False,
) -> dict:
    return {
        "resource_type": "watchlist",
        "resource_id": resource_id,
        "version": version,
        "deleted": deleted,
        "payload": {
            "resource_id": resource_id,
            "name": name,
            "version": version,
            "items": [],
        },
    }


def _snapshot(*resources: dict) -> dict:
    return {
        "snapshot_version": "tenant_research_sync.v1",
        "resources": list(resources),
        "resource_count": len(resources),
        "provider_call_count": 0,
    }


def test_phase6l_reconciliation_is_explicit_and_never_silent_last_write_wins():
    from lib.tenant_research_sync import build_reconciliation_plan

    local = _snapshot(
        _resource("same", version=2),
        _resource("local-newer", version=3),
        _resource("remote-newer", version=1),
        _resource("conflict", version=4, name="Local"),
        _resource("local-delete", version=5, deleted=True),
    )
    remote = _snapshot(
        _resource("same", version=2),
        _resource("local-newer", version=2),
        _resource("remote-newer", version=4),
        _resource("conflict", version=4, name="Remote"),
        _resource("local-delete", version=4),
        _resource("remote-only", version=1),
    )

    plan = build_reconciliation_plan(local, remote)
    states = {row["resource_id"]: row["state"] for row in plan["items"]}
    assert states == {
        "conflict": "conflict",
        "local-delete": "deletion",
        "local-newer": "local-newer",
        "remote-newer": "remote-newer",
        "remote-only": "remote-newer",
        "same": "same-version",
    }
    assert plan["counts"]["conflict"] == 1
    assert plan["counts"]["deletion"] == 1
    assert plan["requires_user_resolution"] is True
    assert plan["strategy"] == "explicit-resolution"


def test_phase6l_sqlite_and_fake_adapters_share_the_snapshot_contract(tmp_path: Path):
    from lib.identity_tenancy import local_test_context
    from lib.research_workspace_db import execute_query, json_dumps
    from lib.tenant_research_desk import TenantResearchDeskStore
    from lib.tenant_research_persistence import (
        DeterministicFakeTenantResearchPersistence,
        SQLiteTenantResearchPersistence,
        TenantResearchRepository,
    )

    context = local_test_context("analyst-a")
    db_path = tmp_path / "account.db"
    execute_query(
        """
        INSERT INTO tenant_watchlists (
            resource_id, tenant_id, owner_user_id, name, source_key,
            source_fingerprint, version, active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
        """,
        (
            "twl_phase6l",
            context["tenant_id"],
            context["user_id"],
            "Daily Radar",
            "local:primary",
            "fingerprint",
            "2026-07-10T08:00:00+00:00",
            "2026-07-10T08:00:00+00:00",
        ),
        db_path=db_path,
    )
    execute_query(
        """
        INSERT INTO tenant_watchlist_items (
            resource_id, tenant_id, watchlist_resource_id, symbol, asset_class,
            display_name, provider, source_status, evidence_json, version,
            active, created_at, updated_at
        ) VALUES (?, ?, ?, 'AAPL', 'equity', 'Apple Inc.', 'saved-fixture',
                  'cached', ?, 1, 1, ?, ?)
        """,
        (
            "twi_phase6l",
            context["tenant_id"],
            "twl_phase6l",
            json_dumps({"source_status": "cached", "private_note": "must-not-sync"}),
            "2026-07-10T08:00:00+00:00",
            "2026-07-10T08:00:00+00:00",
        ),
        db_path=db_path,
    )

    repository = TenantResearchDeskStore(account_db_path=db_path)
    assert isinstance(repository, TenantResearchRepository)
    sqlite_adapter = SQLiteTenantResearchPersistence(repository)
    local_snapshot = sqlite_adapter.snapshot(context)
    fake_adapter = DeterministicFakeTenantResearchPersistence()
    fake_adapter.seed(context, local_snapshot)
    fake_snapshot = fake_adapter.snapshot(context)

    for adapter, snapshot in ((sqlite_adapter, local_snapshot), (fake_adapter, fake_snapshot)):
        assert adapter.health()["provider_call_count"] == 0
        assert snapshot["snapshot_version"] == "tenant_research_sync.v1"
        assert snapshot["resource_count"] >= 1
        assert snapshot["payload_bytes"] <= 30_000
        encoded = json.dumps(snapshot, sort_keys=True).lower()
        assert "tenant_id" not in encoded
        assert "owner_user_id" not in encoded
        assert "private_note" not in encoded


def test_phase6l_first_sync_requires_consent_is_bounded_idempotent_and_tenant_scoped(tmp_path: Path):
    from lib.identity_tenancy import local_test_context
    from lib.tenant_research_persistence import DeterministicFakeTenantResearchPersistence
    from lib.tenant_research_sync import TenantResearchSyncCoordinator

    account_a = local_test_context("analyst-a")
    account_b = local_test_context("analyst-b")
    local = DeterministicFakeTenantResearchPersistence()
    local.seed(account_a, _snapshot(_resource("watch-a")))
    hosted = DeterministicFakeTenantResearchPersistence()
    coordinator = TenantResearchSyncCoordinator(
        db_path=tmp_path / "sync.db",
        local=local,
        hosted=hosted,
    )

    with pytest.raises(ValueError, match="consent"):
        coordinator.queue_first_sync(
            account_a,
            {"consent": False, "idempotency_key": "phase6l-sync-0001"},
        )
    with pytest.raises(ValueError, match="server-derived"):
        coordinator.queue_first_sync(
            account_a,
            {
                "consent": True,
                "idempotency_key": "phase6l-sync-0001",
                "tenant_id": account_b["tenant_id"],
            },
        )

    first = coordinator.queue_first_sync(
        account_a,
        {"consent": True, "idempotency_key": "phase6l-sync-0001"},
    )
    repeated = coordinator.queue_first_sync(
        account_a,
        {"consent": True, "idempotency_key": "phase6l-sync-0001"},
    )
    assert first["status"] == "pending"
    assert repeated["status"] == "deduped"
    assert first["mutation_id"] == repeated["mutation_id"]
    assert first["payload_bytes"] <= 30_000
    assert first["resource_count"] <= 25
    assert coordinator.list_queue(account_b) == []
    encoded = json.dumps(coordinator.list_queue(account_a), sort_keys=True).lower()
    assert "tenant_id" not in encoded
    assert "private" not in encoded
    assert "secret" not in encoded


def test_phase6l_replay_recovers_after_outage_and_conflict_is_not_overwritten(tmp_path: Path):
    from lib.identity_tenancy import local_test_context
    from lib.tenant_research_persistence import DeterministicFakeTenantResearchPersistence
    from lib.tenant_research_sync import TenantResearchSyncCoordinator

    context = local_test_context("analyst-a")
    local = DeterministicFakeTenantResearchPersistence()
    local.seed(context, _snapshot(_resource("watch-a", version=2, name="Local")))
    hosted = DeterministicFakeTenantResearchPersistence(available=False)
    coordinator = TenantResearchSyncCoordinator(
        db_path=tmp_path / "sync.db",
        local=local,
        hosted=hosted,
    )
    coordinator.queue_first_sync(
        context,
        {"consent": True, "idempotency_key": "phase6l-recovery-0001"},
    )

    outage = coordinator.replay(context)
    assert outage["status"] == "offline"
    assert outage["applied_count"] == 0
    assert outage["pending_count"] == 1
    assert outage["provider_call_count"] == 0
    assert coordinator.status(context)["hosted_verified"] is False

    hosted.available = True
    recovered = coordinator.replay(context)
    assert recovered["status"] == "synced"
    assert recovered["applied_count"] == 1
    assert coordinator.status(context)["pending_count"] == 0

    local.seed(context, _snapshot(_resource("watch-a", version=2, name="Changed local")))
    coordinator.queue_first_sync(
        context,
        {"consent": True, "idempotency_key": "phase6l-conflict-0002"},
    )
    conflict = coordinator.replay(context)
    assert conflict["status"] == "conflict"
    assert conflict["conflict_count"] == 1
    assert coordinator.status(context)["conflict_count"] == 1


def test_phase6l_unavailable_hosted_boundary_never_claims_success(tmp_path: Path, monkeypatch):
    from lib.identity_tenancy import local_test_context
    from lib.tenant_research_persistence import (
        DeterministicFakeTenantResearchPersistence,
        SupabaseTenantResearchPersistence,
    )
    from lib.tenant_research_sync import TenantResearchSyncCoordinator

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    context = local_test_context("analyst-a")
    local = DeterministicFakeTenantResearchPersistence()
    local.seed(context, _snapshot(_resource("watch-a")))
    hosted = SupabaseTenantResearchPersistence()
    coordinator = TenantResearchSyncCoordinator(
        db_path=tmp_path / "sync.db",
        local=local,
        hosted=hosted,
    )

    status = coordinator.status(context)
    preview = coordinator.preview(context)
    assert status["state"] == "hosted-unavailable"
    assert status["hosted_verified"] is False
    assert status["hosted_persistence"] == "unavailable"
    assert preview["remote_contacted"] is False
    assert preview["provider_call_count"] == 0
    assert "success" not in status["source_status"]

    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "publishable-test-value")
    configured = SupabaseTenantResearchPersistence().health()
    assert configured["configured"] is True
    assert configured["hosted_verified"] is False
    assert configured["source_status"] == "configured-unverified"
    assert "publishable-test-value" not in json.dumps(configured)


def test_phase6l_http_queue_is_csrf_protected_and_cross_tenant_hidden(tmp_path: Path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api import app as backend_app
    from lib.identity_tenancy import local_test_context
    from lib.research_workspace_db import execute_query

    account_db = tmp_path / "account.db"
    context_a = local_test_context("analyst-a")
    execute_query(
        """
        INSERT INTO tenant_watchlists (
            resource_id, tenant_id, owner_user_id, name, source_key,
            source_fingerprint, version, active, created_at, updated_at
        ) VALUES ('twl_phase6l_http', ?, ?, 'Daily Radar', 'local:primary',
                  'fingerprint', 1, 1, ?, ?)
        """,
        (
            context_a["tenant_id"],
            context_a["user_id"],
            "2026-07-10T08:00:00+00:00",
            "2026-07-10T08:00:00+00:00",
        ),
        db_path=account_db,
    )
    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    backend_app.reset_identity_runtime_for_tests(account_db)
    client = TestClient(backend_app.create_app())

    assert client.get("/api/account/research-desk/sync").status_code == 401
    assert client.post(
        "/api/account/local-session",
        json={"alias": "analyst-a", "return_to": "/?view=watchlist-desk"},
        headers={"Origin": "http://testserver"},
    ).status_code == 201
    csrf_a = client.cookies.get("gt_csrf")
    preview = client.get("/api/account/research-desk/sync/preview")
    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    assert preview_data["state"] == "hosted-unavailable"
    assert preview_data["remote_contacted"] is False
    assert preview_data["local"]["resource_count"] == 1

    body = {"consent": True, "idempotency_key": "phase6l-http-sync-0001"}
    assert client.post("/api/account/research-desk/sync/queue", json=body).status_code == 403
    queued = client.post(
        "/api/account/research-desk/sync/queue",
        json=body,
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf_a},
    )
    assert queued.status_code == 201
    mutation_id = queued.json()["data"]["mutation_id"]
    status_a = client.get("/api/account/research-desk/sync").json()["data"]
    assert status_a["pending_count"] == 1
    assert status_a["hosted_verified"] is False

    assert client.post(
        "/api/account/signout",
        json={},
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf_a},
    ).status_code == 200
    assert client.post(
        "/api/account/local-session",
        json={"alias": "analyst-b", "return_to": "/?view=watchlist-desk"},
        headers={"Origin": "http://testserver"},
    ).status_code == 201
    csrf_b = client.cookies.get("gt_csrf")
    assert client.get("/api/account/research-desk/sync").json()["data"]["pending_count"] == 0
    guessed = client.delete(
        f"/api/account/research-desk/sync/queue/{mutation_id}",
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf_b},
    )
    assert guessed.status_code == 404


def test_phase6l_optional_supabase_sync_schema_is_payload_free_and_rls_first():
    root = Path(__file__).resolve().parents[1]
    migration = (root / "supabase/migrations/20260710212959_phase6l_sync_readiness.sql").read_text(encoding="utf-8").lower()
    assert "global_terminal_sync_receipts" in migration
    assert "global_terminal_deletion_tombstones" in migration
    assert migration.count("enable row level security") == 2
    assert migration.count('create policy "tenant members read"') == 2
    assert migration.count('create policy "tenant owners insert"') == 2
    assert "auth.uid()" in migration
    assert "payload_json" not in migration
    assert "snapshot_json" not in migration
    assert "service_role" not in migration
    assert "hosted_persistence=unavailable" in migration


def test_phase6l_attention_queue_prioritizes_material_unreviewed_source_degradation():
    from lib.tenant_research_desk import build_attention_queue

    queue = build_attention_queue(
        [
            {"resource_id": "reviewed-high", "state": "reviewed", "severity": "high", "source_status": "fresh"},
            {"resource_id": "new-material", "state": "new", "severity": "material", "source_status": "fresh"},
            {"resource_id": "new-degraded", "state": "new", "severity": "material", "source_status": "stale"},
            {"resource_id": "ack-critical", "state": "acknowledged", "severity": "critical", "source_status": "fresh"},
        ]
    )
    assert [row["resource_id"] for row in queue["items"]] == [
        "new-degraded",
        "new-material",
        "reviewed-high",
        "ack-critical",
    ]
    assert queue["attention_count"] == 2
    assert queue["degraded_source_count"] == 1
    assert queue["delivery"] == "in-app-triage-only"
    assert queue["provider_call_count"] == 0


def test_phase6l_performance_harness_passes_local_budgets():
    from scripts.benchmark_phase6l import run

    report = run()
    assert report["passed"] is True
    assert report["checks"]["account_summary"]["p95_ms"] <= 100
    assert report["checks"]["offline_reconciliation"]["p95_ms"] <= 75
    assert report["checks"]["sync_payload"]["bytes"] <= 30_000
    assert report["checks"]["sync_payload"]["resource_count"] <= 25
    assert report["checks"]["sync_provider_calls"]["count"] == 0
