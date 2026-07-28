from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib.research_operations import (
    DEFAULT_REFRESH_PANELS,
    MAX_EXACT_REFRESH_CALLS,
    ResearchOperationsStore,
    ResearchRefreshCoordinator,
    build_observed_provider_health,
    build_refresh_request,
    build_research_operations_contract,
    classify_panel_freshness,
    plan_refresh_budget,
    record_panel_delivery_observations,
)


NOW = datetime(2026, 7, 4, 4, 0, tzinfo=timezone.utc)


def _panel_payload(
    symbol: str = "AAPL",
    *,
    panel: str = "chart-core",
    status: str = "live/fresh",
    provider: str = "yfinance",
    retrieved_at: str = "2026-07-04T03:59:00+00:00",
    observed_at: str = "2026-07-04T03:58:00+00:00",
) -> dict:
    return {
        "contract_version": "phase_2b.v1",
        "data": {
            "workstations": [
                {
                    "identity": {"symbol": symbol, "asset_class": "equity"},
                    "market_clock": {
                        "retrieved_at": retrieved_at,
                        "market_data_as_of": observed_at,
                    },
                    "summary": {
                        "delivery": panel,
                        "fetched_at": retrieved_at,
                        "source_status": status,
                    },
                    "source_register": [
                        {
                            "provider": provider,
                            "source": f"{symbol} {panel}",
                            "source_url": "https://finance.yahoo.com/quote/AAPL",
                            "source_status": status,
                            "fetched_at": retrieved_at,
                            "row_count": 62,
                            "caveat": "Delayed public market observation.",
                            "data_gap": None,
                        }
                    ],
                }
            ]
        },
        "summary": {
            "workstation_count": 1,
            "delivery": panel,
            "source_status": status,
            "fetched_at": retrieved_at,
        },
    }


def test_phase6i_freshness_keeps_retrieval_and_observation_clocks_separate():
    fresh = classify_panel_freshness(
        "chart-core",
        retrieved_at=NOW - timedelta(seconds=60),
        observed_at=NOW - timedelta(seconds=120),
        now=NOW,
    )
    assert fresh["slo_state"] == "within-slo"
    assert fresh["retrieval_age_seconds"] == 60
    assert fresh["observation_age_seconds"] == 120

    old_market = classify_panel_freshness(
        "chart-core",
        retrieved_at=NOW - timedelta(seconds=30),
        observed_at=NOW - timedelta(hours=2),
        now=NOW,
    )
    assert old_market["retrieval_slo_state"] == "within-slo"
    assert old_market["observation_slo_state"] == "stale"
    assert old_market["slo_state"] == "stale"


def test_phase6i_missing_clock_is_not_zero_or_fresh():
    row = classify_panel_freshness(
        "financials",
        retrieved_at=None,
        observed_at=None,
        now=NOW,
    )
    assert row["retrieval_age_seconds"] is None
    assert row["observation_age_seconds"] is None
    assert row["slo_state"] == "unavailable"


def test_phase6i_observed_provider_health_does_not_promote_configured_only():
    rows = build_observed_provider_health(
        [
            {
                "provider": "yfinance",
                "panel": "chart-core",
                "source_status": "live/fresh",
                "retrieved_at": NOW.isoformat(),
                "source_url": "https://finance.yahoo.com/quote/AAPL",
            },
            {
                "provider": "sec_edgar",
                "panel": "financials",
                "source_status": "cached",
                "retrieved_at": NOW.isoformat(),
                "source_url": "https://data.sec.gov/",
            },
        ],
        configured_providers=["Alpha Vantage"],
    )
    by_provider = {row["provider"]: row for row in rows}
    assert by_provider["yfinance"]["contacted"] is True
    assert by_provider["yfinance"]["successful"] is True
    assert by_provider["sec_edgar"]["status"] == "cached"
    assert by_provider["Alpha Vantage"]["status"] == "configured"
    assert by_provider["Alpha Vantage"]["contacted"] is False
    assert by_provider["Alpha Vantage"]["successful"] is False


def test_phase6i_default_exact_refresh_budget_is_precomputed_and_bounded():
    budget = plan_refresh_budget(DEFAULT_REFRESH_PANELS, asset_class="equity")
    assert budget["planned_calls"] == MAX_EXACT_REFRESH_CALLS == 8
    assert budget["hard_ceiling"] == 8
    assert budget["broad_universe_fanout"] is False
    with pytest.raises(ValueError, match="provider-call ceiling"):
        plan_refresh_budget(
            [
                "chart-core",
                "technicals",
                "financials",
                "news",
                "comparison",
            ],
            asset_class="equity",
        )


def test_phase6i_exact_request_rejects_unknown_panel_and_unsafe_symbol():
    with pytest.raises(ValueError, match="panel"):
        build_refresh_request("AAPL", panels=["orders"])
    with pytest.raises(ValueError, match="symbol"):
        build_refresh_request("../AAPL", panels=["chart-core"])


def test_phase6i_store_bounds_history_and_redacts_private_fields(tmp_path: Path):
    store = ResearchOperationsStore(tmp_path / "workspace.db", max_jobs=3)
    for index in range(5):
        request = build_refresh_request(
            "AAPL",
            panels=["chart-core"],
            idempotency_key=f"safe-{index}",
        )
        job = store.create_job(request, now=NOW + timedelta(seconds=index))
        store.update_job(
            job["job_id"],
            status="completed",
            events=[
                {
                    "status": "completed",
                    "at": NOW.isoformat(),
                    "api_key": "must-not-appear",
                    "local_path": "C:\\private\\workspace.db",
                }
            ],
            now=NOW + timedelta(seconds=index),
        )
    rows = store.list_jobs("AAPL", limit=100)
    assert len(rows) == 3
    serialized = json.dumps(rows)
    assert "must-not-appear" not in serialized
    assert "C:\\\\private" not in serialized


def test_phase6i_queue_is_idempotent_and_rejects_same_symbol_overlap(tmp_path: Path):
    store = ResearchOperationsStore(tmp_path / "workspace.db")
    coordinator = ResearchRefreshCoordinator(
        store=store,
        panel_fetcher=lambda request, panel: _panel_payload(panel=panel),
        auto_start=False,
        now_fn=lambda: NOW,
    )
    request = build_refresh_request("AAPL", panels=["chart-core"])
    first = coordinator.submit(request)
    same = coordinator.submit(request)
    overlap = coordinator.submit(
        build_refresh_request("AAPL", panels=["financials"])
    )
    assert first["status"] == "queued"
    assert same["job_id"] == first["job_id"]
    assert same["idempotent_reuse"] is True
    assert overlap["status"] == "overlap"
    assert overlap["overlap_job_id"] == first["job_id"]


def test_phase6i_success_separates_last_attempt_and_last_success(tmp_path: Path):
    store = ResearchOperationsStore(tmp_path / "workspace.db")
    coordinator = ResearchRefreshCoordinator(
        store=store,
        panel_fetcher=lambda request, panel: _panel_payload(panel=panel),
        auto_start=False,
        now_fn=lambda: NOW,
    )
    request = build_refresh_request("AAPL", panels=["chart-core"])
    queued = coordinator.submit(request)
    completed = coordinator.run(queued["job_id"])
    contract = build_research_operations_contract(
        request,
        store=store,
        now=NOW,
    )
    assert completed["status"] == "completed"
    assert contract["last_attempt"]["job_id"] == completed["job_id"]
    assert contract["last_success"]["job_id"] == completed["job_id"]
    assert contract["last_attempt_at"]
    assert contract["last_success_at"]


def test_phase6i_failure_retains_same_symbol_lkg_and_sets_retry(tmp_path: Path):
    store = ResearchOperationsStore(tmp_path / "workspace.db")
    success = ResearchRefreshCoordinator(
        store=store,
        panel_fetcher=lambda request, panel: _panel_payload(panel=panel),
        auto_start=False,
        now_fn=lambda: NOW,
    )
    first = success.submit(
        build_refresh_request("AAPL", panels=["chart-core"], idempotency_key="ok")
    )
    success.run(first["job_id"])

    failed = ResearchRefreshCoordinator(
        store=store,
        panel_fetcher=lambda request, panel: _panel_payload(
            panel=panel,
            status="rate-limited",
        ),
        auto_start=False,
        now_fn=lambda: NOW + timedelta(minutes=1),
    )
    second = failed.submit(
        build_refresh_request("AAPL", panels=["chart-core"], idempotency_key="rate")
    )
    terminal = failed.run(second["job_id"])
    contract = build_research_operations_contract(
        build_refresh_request("AAPL", panels=["chart-core"]),
        store=store,
        now=NOW + timedelta(minutes=1),
    )
    assert terminal["status"] == "rate-limited"
    assert terminal["retained_lkg"] is True
    assert contract["last_attempt"]["job_id"] == terminal["job_id"]
    assert contract["last_success"]["job_id"] == first["job_id"]
    assert contract["next_safe_retry_at"]
    assert contract["retry_reason"] == "provider-rate-limit"


def test_phase6i_usable_panel_with_provider_failure_is_partial(tmp_path: Path):
    store = ResearchOperationsStore(tmp_path / "workspace.db")

    def mixed_fetcher(request, panel):
        payload = _panel_payload(panel=panel)
        payload["data"]["workstations"][0]["source_register"].append(
            {
                "provider": "supplemental",
                "source": "supplemental context",
                "source_url": "https://example.com/provider",
                "source_status": "provider-error",
                "fetched_at": NOW.isoformat(),
                "row_count": 0,
                "data_gap": "Provider failed while primary evidence remained usable.",
            }
        )
        return payload

    coordinator = ResearchRefreshCoordinator(
        store=store,
        panel_fetcher=mixed_fetcher,
        auto_start=False,
        now_fn=lambda: NOW,
    )
    queued = coordinator.submit(
        build_refresh_request("AAPL", panels=["chart-core"])
    )
    terminal = coordinator.run(queued["job_id"])
    assert terminal["status"] == "partial"
    assert terminal["failed_calls"] == 1
    assert terminal["panel_results"][0]["status"] == "completed"


def test_phase6i_panel_observations_are_exact_and_cross_symbol_is_rejected(
    tmp_path: Path,
):
    store = ResearchOperationsStore(tmp_path / "workspace.db")
    request = build_refresh_request("AAPL", panels=["chart-core"])
    rows = record_panel_delivery_observations(
        store,
        request,
        "chart-core",
        _panel_payload("AAPL"),
        attempted_at=NOW,
    )
    assert rows and {row["symbol"] for row in rows} == {"AAPL"}
    with pytest.raises(ValueError, match="identity"):
        record_panel_delivery_observations(
            store,
            request,
            "chart-core",
            _panel_payload("TSLA"),
            attempted_at=NOW,
        )
    assert store.list_panel_observations("TSLA") == []


def test_phase6i_native_symbol_contract_is_observable_without_api_envelope(
    tmp_path: Path,
):
    store = ResearchOperationsStore(tmp_path / "workspace.db")
    request = build_refresh_request("AAPL", panels=["chart-core"])
    native = _panel_payload("AAPL")["data"]
    rows = record_panel_delivery_observations(
        store,
        request,
        "chart-core",
        native,
        attempted_at=NOW,
    )
    assert rows[0]["provider"] == "yfinance"
    assert rows[0]["symbol"] == "AAPL"


def test_phase6i_contract_has_no_hosted_delivery_or_execution_claim(tmp_path: Path):
    store = ResearchOperationsStore(tmp_path / "workspace.db")
    contract = build_research_operations_contract(
        build_refresh_request("AAPL", panels=["chart-core"]),
        store=store,
        now=NOW,
    )
    assert contract["runtime_truth"] == {
        "process_local_worker": True,
        "installed_background_service": False,
        "hosted_scheduler": False,
        "notification_delivery": False,
        "remote_control": False,
        "kill_switch_ready": True,
        "broker_execution": False,
        "autonomous_ai_action": False,
    }
    assert contract["not_financial_advice"] is True


def test_phase6i_web_surface_declares_accessible_operational_states():
    source = Path(
        "apps/web/src/components/AnalystWorkspace.tsx"
    ).read_text(encoding="utf-8")
    proxy = Path(
        "apps/web/src/app/api/runtime/[...path]/route.ts"
    ).read_text(encoding="utf-8")
    for marker in (
        "data-phase6i-research-operations",
        "Refresh exact workspace",
        'role="status"',
        'aria-live="polite"',
        "last-success",
        "next-safe-retry",
    ):
        assert marker in source
    assert "export async function POST" in proxy
    assert "analyst-workspace/" in proxy


def test_phase6i_api_etag_validation_and_bounded_refresh(monkeypatch, tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api import app as backend_app
    from lib.api_contracts import validate_api_payload
    from lib.research_operations import ResearchOperationsStore

    isolated_store = ResearchOperationsStore(tmp_path / "phase6i-etag.db")
    monkeypatch.setattr(backend_app, "get_default_operations_store", lambda: isolated_store)
    client = TestClient(backend_app.create_app())
    response = client.get(
        "/api/analyst-workspace/AAPL/operations",
        params={
            "asset_class": "equity",
            "interval": "1d",
            "range": "3mo",
            "panels": "chart-core,financials,catalysts,sources",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["payload_type"] == "research_operations"
    assert payload["data"]["budget"]["hard_ceiling"] == 8
    assert len(response.content) < 30_000
    assert validate_api_payload(payload)[0] is True

    conditional = client.get(
        "/api/analyst-workspace/AAPL/operations",
        params={
            "asset_class": "equity",
            "interval": "1d",
            "range": "3mo",
            "panels": "chart-core,financials,catalysts,sources",
        },
        headers={"If-None-Match": response.headers["etag"]},
    )
    assert conditional.status_code == 304

    invalid_panel = client.get(
        "/api/analyst-workspace/AAPL/operations",
        params={"panels": "orders"},
    )
    assert invalid_panel.status_code == 422
    assert client.get("/api/analyst-workspace/NOTAREAL123/operations").status_code == 404

    fake_job = {
        "job_id": "research_refresh_0123456789ab",
        "request_id": "request-safe",
        "symbol": "AAPL",
        "asset_class": "equity",
        "interval": "1d",
        "range": "3mo",
        "panels": ["chart-core"],
        "status": "queued",
        "planned_calls": 1,
        "actual_calls": 0,
        "retained_lkg": False,
        "events": [{"status": "queued", "at": NOW.isoformat()}],
        "not_financial_advice": True,
    }
    monkeypatch.setattr(backend_app, "submit_exact_refresh", lambda request: fake_job)
    queued = client.post(
        "/api/analyst-workspace/AAPL/refresh",
        json={
            "asset_class": "equity",
            "interval": "1d",
            "range": "3mo",
            "panels": ["chart-core"],
            "idempotency_key": "api-test",
        },
    )
    assert queued.status_code == 202
    assert queued.json()["data"]["status"] == "queued"
    assert client.post(
        "/api/analyst-workspace/AAPL/refresh",
        json={"panels": ["orders"]},
    ).status_code == 422
    assert client.get(
        "/api/research-operations/jobs/research_refresh_BAD"
    ).status_code == 422


def test_phase6i_bounded_panel_response_cache_is_symbol_scoped():
    from backend.api import app as backend_app

    backend_app._PANEL_RESPONSE_CACHE.clear()
    key = backend_app._panel_response_cache_key(
        symbol="AAPL",
        panel="chart-core",
        asset_class="equity",
        interval="1d",
        range_name="3mo",
        chart_type="candlestick",
        compare=None,
    )
    payload = {"summary": {"status": "cached"}}
    backend_app._store_cached_panel_response(key, payload)
    assert backend_app._get_cached_panel_response(key) == payload

    backend_app._invalidate_panel_response_cache("MSFT")
    assert backend_app._get_cached_panel_response(key) == payload

    backend_app._invalidate_panel_response_cache("aapl")
    assert backend_app._get_cached_panel_response(key) is None
