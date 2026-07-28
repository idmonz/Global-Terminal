from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


NOW = datetime(2026, 7, 10, 3, 0, tzinfo=timezone.utc)


def _snapshot(symbol: str, price: float, *, status: str = "cached") -> dict:
    return {
        "symbol": symbol,
        "asset_class": "equity",
        "quote": {
            "last_price": price,
            "provider": "phase6k.saved-fixture",
            "source_url": f"https://example.invalid/{symbol.lower()}",
            "source_status": status,
            "retrieved_at": "2026-07-10T02:00:00+00:00",
            "observed_at": "2026-07-09T20:00:00+00:00",
        },
        "performance": {"return_1w_pct": 2.0, "return_1m_pct": 4.0, "return_3m_pct": 6.0},
        "financials": {"metrics": {"market_cap": 100_000_000_000, "pe_ratio": 25.0}},
        "catalysts": {"earnings": [], "dividends": [], "news": []},
        "source_status": status,
        "fetched_at": "2026-07-10T02:00:00+00:00",
        "source_register": [
            {
                "provider": "phase6k.saved-fixture",
                "source_url": f"https://example.invalid/{symbol.lower()}",
                "source_status": status,
                "fetched_at": "2026-07-10T02:00:00+00:00",
            }
        ],
    }


def _seed_local_watchlist(db_path: Path) -> None:
    from lib.research_workspace_db import execute_query, json_dumps

    execute_query(
        """
        INSERT INTO watchlist_collections (list_id, name, position, active, created_at, updated_at, metadata_json)
        VALUES (?, ?, 0, 1, ?, ?, '{}')
        """,
        ("primary", "Local Daily Radar", NOW.isoformat(), NOW.isoformat()),
        db_path=db_path,
    )
    for position, symbol in enumerate(("AAPL", "TSLA")):
        execute_query(
            """
            INSERT INTO watchlist_items (
                item_id, watchlist_id, position, item_type, symbol, display_name,
                asset_class, exchange, tags, watch_reason, source, active,
                created_at, updated_at, metadata_json
            ) VALUES (?, 'primary', ?, 'equity', ?, ?, 'equity', 'NASDAQ', '[]', ?, 'phase6k-local', 1, ?, ?, '{}')
            """,
            (
                f"local_item_{position}",
                position,
                symbol,
                f"{symbol} Local",
                f"private thesis for {symbol}",
                NOW.isoformat(),
                NOW.isoformat(),
            ),
            db_path=db_path,
        )
    previous = [_snapshot("AAPL", 100.0), _snapshot("TSLA", 200.0)]
    current = [_snapshot("AAPL", 108.0), _snapshot("TSLA", 194.0, status="stale")]
    for index, rows in enumerate((previous, current)):
        started = NOW - timedelta(hours=2 - index)
        execute_query(
            """
            INSERT INTO watchlist_materialization_jobs (
                job_id, list_id, status, requested_count, completed_count,
                provider_call_budget, provider_call_count, interval, range_name,
                started_at, completed_at, rows_json, created_at
            ) VALUES (?, 'primary', 'completed', 2, 2, 8, 0, '1d', '3mo', ?, ?, ?, ?)
            """,
            (
                f"job_phase6k_{index}",
                started.isoformat(),
                started.isoformat(),
                json_dumps(rows),
                started.isoformat(),
            ),
            db_path=db_path,
        )


def _store(tmp_path: Path):
    from lib.tenant_research_desk import TenantResearchDeskStore

    local_db = tmp_path / "local.db"
    account_db = tmp_path / "account.db"
    _seed_local_watchlist(local_db)
    return TenantResearchDeskStore(account_db_path=account_db, local_db_path=local_db)


def _import_for(store, context):
    preview = store.preview_import(context, source_list_id="primary")
    return store.confirm_import(
        context,
        {
            "preview_id": preview["preview_id"],
            "candidate_ids": [row["candidate_id"] for row in preview["candidates"]],
            "consent": True,
            "idempotency_key": "phase6k-import-0001",
            "expected_version": 0,
            "destination_name": "Account Daily Radar",
        },
    )


def test_phase6k_preview_is_bounded_read_only_and_private_field_free(tmp_path: Path):
    from lib.identity_tenancy import local_test_context

    store = _store(tmp_path)
    context = local_test_context("analyst-a")
    before = store.summary(context)
    preview = store.preview_import(context, source_list_id="primary", limit=25)
    after = store.summary(context)
    assert preview["candidate_count"] == 2
    assert preview["provider_call_count"] == 0
    assert preview["bounded_limit"] == 25
    assert preview["excluded_fields"] == ["metadata_json", "watch_reason"]
    assert before["watchlist_count"] == after["watchlist_count"] == 0
    assert "private thesis" not in str(preview).lower()


def test_phase6k_import_requires_consent_is_idempotent_and_reports_conflict(tmp_path: Path):
    from lib.identity_tenancy import local_test_context
    from lib.tenant_research_desk import TenantResearchConflict

    store = _store(tmp_path)
    context = local_test_context("analyst-a")
    preview = store.preview_import(context, source_list_id="primary")
    body = {
        "preview_id": preview["preview_id"],
        "candidate_ids": [row["candidate_id"] for row in preview["candidates"]],
        "consent": False,
        "idempotency_key": "phase6k-import-0001",
        "expected_version": 0,
        "destination_name": "Account Daily Radar",
    }
    with pytest.raises(ValueError, match="consent"):
        store.confirm_import(context, body)
    assert store.summary(context)["watchlist_count"] == 0

    first = store.confirm_import(context, {**body, "consent": True})
    repeated = store.confirm_import(context, {**body, "consent": True})
    assert first["status"] == "imported"
    assert repeated["status"] == "deduped"
    assert first["watchlist"]["resource_id"] == repeated["watchlist"]["resource_id"]
    assert first["watchlist"]["item_count"] == 2
    assert store.summary(context)["watchlist_count"] == 1

    with pytest.raises(TenantResearchConflict) as conflict:
        store.confirm_import(
            context,
            {**body, "consent": True, "idempotency_key": "phase6k-import-0002"},
        )
    assert conflict.value.current_version == 1


def test_phase6k_cancel_and_client_identity_fields_change_nothing(tmp_path: Path):
    from lib.identity_tenancy import local_test_context
    from lib.tenant_research_desk import validate_import_body

    store = _store(tmp_path)
    context = local_test_context("analyst-a")
    preview = store.preview_import(context, source_list_id="primary")
    canceled = store.cancel_import(context, preview_id=preview["preview_id"])
    assert canceled["status"] == "canceled"
    assert store.summary(context)["watchlist_count"] == 0
    with pytest.raises(ValueError, match="server-derived"):
        validate_import_body({"tenant_id": "other", "consent": True})


def test_phase6k_account_b_cannot_observe_or_mutate_account_a(tmp_path: Path):
    from lib.identity_tenancy import local_test_context

    store = _store(tmp_path)
    account_a = local_test_context("analyst-a")
    account_b = local_test_context("analyst-b")
    imported = _import_for(store, account_a)
    resource_id = imported["watchlist"]["resource_id"]
    assert store.list_watchlists(account_a)[0]["resource_id"] == resource_id
    assert store.list_watchlists(account_b) == []
    assert store.get_watchlist(account_b, resource_id) is None
    assert store.delete_watchlist(account_b, resource_id, expected_version=1) is False
    assert store.export(account_b)["watchlists"] == []
    exported_a = store.export(account_a)
    assert exported_a["watchlists"][0]["item_count"] == 2
    assert exported_a["consent_receipts"][0]["selected_count"] == 2
    assert exported_a["consent_receipts"][0]["excluded_fields"] == ["metadata_json", "watch_reason"]
    assert exported_a["retention"] == {"inbox_days": 90, "consent_receipt_days": 365}
    assert "private thesis" not in str(exported_a).lower()
    assert "tenant_id" not in str(exported_a).lower()
    first_item = exported_a["watchlists"][0]["items"][0]
    assert first_item["provider"] == "phase6k.saved-fixture"
    assert first_item["source_status"] in {"cached", "stale"}
    assert first_item["observed_at"]
    assert first_item["retrieved_at"]
    assert "originView=watchlist-desk" in first_item["research_href"]


def test_phase6k_saved_change_scan_dedupes_and_acknowledges_tenant_inbox(tmp_path: Path):
    from lib.identity_tenancy import local_test_context

    store = _store(tmp_path)
    account_a = local_test_context("analyst-a")
    account_b = local_test_context("analyst-b")
    imported = _import_for(store, account_a)
    watchlist_id = imported["watchlist"]["resource_id"]
    rule = store.configure_rule(
        account_a,
        watchlist_id,
        enabled=True,
        minimum_severity="material",
        cooldown_minutes=60,
        expected_version=0,
        now=NOW,
    )
    assert rule["delivery"] == "in-app-only"
    first = store.scan_inbox(account_a, watchlist_id, now=NOW)
    second = store.scan_inbox(account_a, watchlist_id, now=NOW + timedelta(minutes=1))
    assert first["provider_call_count"] == 0
    assert first["stored_count"] >= 1
    assert second["stored_count"] == 0
    assert second["status"] in {"deduped", "cooldown"}
    inbox = store.list_inbox(account_a, now=NOW)
    assert inbox
    assert store.list_inbox(account_b, now=NOW) == []
    item_id = inbox[0]["resource_id"]
    assert store.get_inbox_item(account_b, item_id) is None
    reviewed = store.update_inbox_state(account_a, item_id, state="reviewed", expected_version=1, now=NOW)
    acknowledged = store.update_inbox_state(
        account_a,
        item_id,
        state="acknowledged",
        expected_version=reviewed["version"],
        now=NOW + timedelta(minutes=2),
    )
    assert acknowledged["state"] == "acknowledged"
    assert acknowledged["delivery_status"] == "delivery-unavailable"
    assert acknowledged["expires_at"]
    assert "originView=watchlist-desk" in acknowledged["research_href"]
    assert store.get_inbox_item(account_b, item_id) is None
    from lib.tenant_research_desk import TenantResearchDeskStore

    restored_store = TenantResearchDeskStore(
        account_db_path=store.account_db_path,
        local_db_path=store.local_db_path,
    )
    assert restored_store.get_inbox_item(account_a, item_id)["state"] == "acknowledged"
    with pytest.raises(ValueError, match="backward"):
        store.update_inbox_state(
            account_a,
            item_id,
            state="reviewed",
            expected_version=acknowledged["version"],
            now=NOW + timedelta(minutes=3),
        )


def test_phase6k_kill_switch_and_expiry_are_honest(tmp_path: Path):
    from lib.identity_tenancy import local_test_context

    store = _store(tmp_path)
    context = local_test_context("analyst-a")
    imported = _import_for(store, context)
    watchlist_id = imported["watchlist"]["resource_id"]
    store.configure_rule(
        context,
        watchlist_id,
        enabled=True,
        minimum_severity="material",
        cooldown_minutes=0,
        expected_version=0,
        expires_at=(NOW + timedelta(hours=1)).isoformat(),
        now=NOW,
    )
    suppressed = store.scan_inbox(context, watchlist_id, now=NOW, kill_switch=True)
    assert suppressed["status"] == "suppressed"
    assert suppressed["stored_count"] == 0
    expired = store.scan_inbox(context, watchlist_id, now=NOW + timedelta(hours=2))
    assert expired["status"] == "expired"
    assert expired["stored_count"] == 0


def test_phase6k_delete_cleans_tenant_children_only(tmp_path: Path):
    from lib.identity_tenancy import local_test_context

    store = _store(tmp_path)
    account_a = local_test_context("analyst-a")
    imported = _import_for(store, account_a)
    watchlist_id = imported["watchlist"]["resource_id"]
    store.configure_rule(account_a, watchlist_id, enabled=True, expected_version=0, now=NOW)
    store.scan_inbox(account_a, watchlist_id, now=NOW)
    assert store.delete_watchlist(account_a, watchlist_id, expected_version=1) is True
    exported = store.export(account_a)
    assert exported["watchlists"] == []
    assert exported["inbox"] == []
    assert exported["rules"] == []
    assert exported["consent_receipts"] == []


def test_phase6k_http_journey_and_cross_tenant_404(monkeypatch, tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api import app as backend_app

    local_db = tmp_path / "local.db"
    account_db = tmp_path / "account.db"
    _seed_local_watchlist(local_db)
    monkeypatch.setenv("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_WORKSPACE_DB_PATH", str(local_db))
    backend_app.reset_identity_runtime_for_tests(account_db)
    client = TestClient(backend_app.create_app())

    assert client.get("/api/account/research-desk").status_code == 401
    assert client.post(
        "/api/account/local-session",
        json={"alias": "analyst-a", "return_to": "/?view=watchlist-desk"},
        headers={"Origin": "http://testserver"},
    ).status_code == 201
    csrf = client.cookies.get("gt_csrf")
    preview_response = client.get("/api/account/research-desk/imports/preview?source_list_id=primary")
    assert preview_response.status_code == 200
    preview = preview_response.json()["data"]
    import_body = {
        "preview_id": preview["preview_id"],
        "candidate_ids": [row["candidate_id"] for row in preview["candidates"]],
        "consent": True,
        "idempotency_key": "phase6k-http-import",
        "expected_version": 0,
        "destination_name": "Account Daily Radar",
    }
    assert client.post("/api/account/research-desk/imports", json=import_body).status_code == 403
    imported = client.post(
        "/api/account/research-desk/imports",
        json=import_body,
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
    )
    assert imported.status_code == 201
    watchlist_id = imported.json()["data"]["watchlist"]["resource_id"]
    rule = client.put(
        f"/api/account/research-desk/watchlists/{watchlist_id}/rule",
        json={"enabled": True, "minimum_severity": "material", "cooldown_minutes": 60, "expected_version": 0},
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
    )
    assert rule.status_code == 200
    scanned = client.post(
        f"/api/account/research-desk/watchlists/{watchlist_id}/inbox",
        json={},
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
    )
    assert scanned.status_code == 200
    desk = client.get("/api/account/research-desk").json()["data"]
    assert desk["summary"]["watchlist_count"] == 1
    assert desk["summary"]["inbox_count"] >= 1
    inbox_id = desk["inbox"][0]["resource_id"]
    reviewed = client.patch(
        f"/api/account/research-desk/inbox/{inbox_id}",
        json={"state": "reviewed", "expected_version": 1},
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
    )
    assert reviewed.status_code == 200

    assert client.post(
        "/api/account/signout",
        json={},
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
    ).status_code == 200
    assert client.post(
        "/api/account/local-session",
        json={"alias": "analyst-b", "return_to": "/?view=watchlist-desk"},
        headers={"Origin": "http://testserver"},
    ).status_code == 201
    assert client.get(f"/api/account/research-desk/watchlists/{watchlist_id}").status_code == 404
    assert client.get(f"/api/account/research-desk/inbox/{inbox_id}").status_code == 404
    account_b = client.get("/api/account/research-desk").json()["data"]
    assert account_b["summary"]["watchlist_count"] == 0
    assert account_b["summary"]["inbox_count"] == 0


def test_phase6k_web_journey_is_lazy_consentful_and_source_aware():
    root = Path(__file__).resolve().parents[1]
    component = (root / "apps/web/src/components/TenantResearchDesk.tsx").read_text(encoding="utf-8")
    watchlist = (root / "apps/web/src/components/WatchlistDesk.tsx").read_text(encoding="utf-8")
    css = (root / "apps/web/src/app/globals.css").read_text(encoding="utf-8")
    for marker in (
        'data-phase6k-tenant-research="true"',
        "Account research",
        "Preview local import",
        "I consent to copy the selected public research fields",
        "External delivery unavailable",
        'aria-live="polite"',
        'credentials: "same-origin"',
        'readCookie("gt_csrf")',
        "/api/account/research-desk",
        "Review",
        "Acknowledge",
    ):
        assert marker in component
    assert "<TenantResearchDesk" in watchlist
    assert ".tenant-research-desk" in css
    assert ".tenant-import-preview" in css
    assert "private thesis" not in component.lower()


def test_phase6k_same_origin_proxy_is_bounded_and_research_desk_allowlisted():
    root = Path(__file__).resolve().parents[1]
    proxy = (root / "apps/web/src/app/api/account/[...path]/route.ts").read_text(encoding="utf-8")
    assert "research-desk" in proxy
    assert 'method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE"' in proxy
    assert "const MAX_BODY_BYTES = 16_384" in proxy
    assert "sameOrigin(request)" in proxy
    assert "X-CSRF-Token" in proxy
    assert 'export function PATCH' in proxy


def test_phase6k_optional_supabase_schema_is_rls_first_and_not_claimed_live():
    root = Path(__file__).resolve().parents[1]
    migration = (root / "supabase/migrations/20260710164600_phase6k_tenant_research.sql").read_text(encoding="utf-8")
    assert migration.count("enable row level security") == 5
    assert "tenant members read" in migration
    assert "tenant members insert" in migration
    assert "tenant members update" in migration
    assert "tenant members delete" in migration
    assert "auth.uid()" in migration
    assert migration.count("foreign key (tenant_id") == 5
    assert "with check (owner_user_id = (select auth.uid()) and exists" in migration
    assert "hosted_persistence=unavailable" in migration
    assert "service_role" not in migration.lower()
