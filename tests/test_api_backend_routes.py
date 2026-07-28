from __future__ import annotations

import pytest

from backend.api import app as backend_app
from lib.api_contracts import validate_api_payload


def _assert_valid(payload: dict) -> None:
    valid, issues = validate_api_payload(payload)
    assert valid, issues


def test_backend_route_getters_are_import_safe_without_fastapi_runtime():
    payloads = [
        backend_app.get_api_manifest(),
        backend_app.get_product_parity_payload(),
        backend_app.get_runtime_health_payload(),
        backend_app.get_market_intelligence_payload(include_runtime=False),
        backend_app.get_equity_intelligence_payload(symbol="AAPL", include_runtime=False),
        backend_app.get_financial_fundamentals_payload(symbol="AAPL", include_runtime=False),
        backend_app.get_options_quant_payload(symbol="AAPL", include_runtime=False),
        backend_app.get_screener_drilldown_payload(include_runtime=False),
        backend_app.get_crypto_intelligence_payload(symbol="BTCUSDT", include_runtime=False),
        backend_app.get_symbol_directory_payload(query="micro", limit=5),
        backend_app.get_symbol_workstation_payload(symbol="MSFT", asset_class="equity", runtime_mode="fixture"),
        backend_app.get_feeds_payload(),
        backend_app.get_provider_health_payload(),
        backend_app.get_layers_payload(include_runtime=False),
        backend_app.get_news_payload(include_runtime=False),
        backend_app.get_war_room_payload(include_runtime=False),
        backend_app.get_ai_providers_payload(),
        backend_app.get_asset_universe_payload(),
        backend_app.get_event_asset_graph_payload(include_runtime=False),
        backend_app.get_command_workspace_payload(include_runtime=False),
        backend_app.get_war_room_map_payload(include_runtime=False),
        backend_app.get_map_news_event_fusion_payload(include_runtime=False),
        backend_app.get_war_room_map_replay_payload(db_path=None),
        backend_app.get_research_report_payload(include_runtime=False),
        backend_app.get_research_memory_payload(mode="demo"),
    ]

    for payload in payloads:
        _assert_valid(payload)

    assert backend_app.app is None if not backend_app.FASTAPI_AVAILABLE else backend_app.app is not None


def test_optional_fastapi_routes_smoke_when_dependency_is_installed():
    if not backend_app.FASTAPI_AVAILABLE:
        pytest.skip("FastAPI is optional and not installed in this environment.")
    try:
        from fastapi.testclient import TestClient
    except Exception as exc:  # pragma: no cover - depends on optional dependency stack
        pytest.skip(f"FastAPI TestClient unavailable: {exc}")

    client = TestClient(backend_app.app)
    routes = [
        "/api",
        "/api/runtime-health",
        "/api/product-parity",
        "/api/market-intelligence",
        "/api/equity-intelligence",
        "/api/financial-fundamentals",
        "/api/options-quant",
            "/api/screener-drilldown",
            "/api/market-map-screener",
        "/api/market-map-screens",
        "/api/crypto-intelligence",
        "/api/symbol-directory",
        "/api/symbol-workstation",
        "/api/feeds",
        "/api/provider-health",
        "/api/layers",
        "/api/news",
        "/api/war-room",
        "/api/ai-providers",
        "/api/asset-universe",
        "/api/event-asset-graph",
        "/api/command-workspace",
        "/api/war-room-map",
        "/api/map-news-event-fusion",
        "/api/war-room-map-snapshots",
        "/api/war-room-map-replay",
        "/api/research-report",
        "/api/research-memory?mode=demo&collection=demo-research&surface=inbox",
    ]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
        _assert_valid(response.json())


def test_saved_market_screen_routes_use_private_post_bodies(monkeypatch, tmp_path):
    if not backend_app.FASTAPI_AVAILABLE:
        pytest.skip("FastAPI is optional and not installed in this environment.")
    from fastapi.testclient import TestClient

    monkeypatch.setenv("RESEARCH_WORKSPACE_DB_PATH", str(tmp_path / "market-screens.db"))
    client = TestClient(backend_app.app)
    definition = {
        "universe": "bounded-us-largecap",
        "sectors": ["Technology"],
        "market_cap": "mega",
        "return_1d": "all",
        "return_1m": "positive",
        "volatility": "moderate",
        "rsi": "constructive",
        "trend": "above-sma20",
        "valuation": "available",
        "quality": "complete",
        "rank": "balanced",
        "display": "heatmap",
    }
    created = client.post("/api/market-map-screens", json={"name": "Morning quality", "definition": definition})
    assert created.status_code == 200
    screen = created.json()["screen"]
    assert screen["privacy_scope"] == "local-private"

    listed = client.get("/api/market-map-screens")
    assert listed.status_code == 200
    assert listed.json()["screens"][0]["name"] == "Morning quality"

    renamed = client.patch(f"/api/market-map-screens/{screen['screen_id']}", json={"name": "Opening screen"})
    assert renamed.status_code == 200
    assert renamed.json()["screen"]["name"] == "Opening screen"

    archived = client.delete(f"/api/market-map-screens/{screen['screen_id']}")
    assert archived.status_code == 200
    assert client.get("/api/market-map-screens").json()["screens"] == []


def test_war_room_map_snapshot_routes_capture_dedupe_and_compare(monkeypatch, tmp_path):
    if not backend_app.FASTAPI_AVAILABLE:
        pytest.skip("FastAPI is optional and not installed in this environment.")
    from fastapi.testclient import TestClient

    monkeypatch.setenv("RESEARCH_WORKSPACE_DB_PATH", str(tmp_path / "map-replay.db"))
    marker_state = {"severity": "watch", "second": False}

    def current_payload(*, include_runtime: bool = False):
        markers = [{
            "marker_id": "marker:event-a", "event_id": "event-a", "title": "Observed A",
            "lat": 37.5, "lon": 127.0, "coordinate_method": "provider_coordinates",
            "coordinate_status": "source-backed", "provider": "usgs", "source": "USGS",
            "source_url": "https://example.test/event-a", "fetched_at": "2026-06-22T01:00:00+00:00",
            "timestamp": "2026-06-22T00:55:00+00:00", "source_status": "live/fresh",
            "freshness": "live/fresh", "confidence": 0.9, "severity": marker_state["severity"],
            "region": "East Asia", "layer_ids": ["earthquakes"], "caveat": "Observed row.", "data_gap": "",
        }]
        if marker_state["second"]:
            markers.append({**markers[0], "marker_id": "marker:event-b", "event_id": "event-b", "title": "Observed B", "source_url": "https://example.test/event-b"})
        return {
            "contract_version": "phase_2b.v1", "payload_type": "map_news_event_fusion", "generated_at": "2026-06-22T01:00:00+00:00",
            "data": {"markers": markers, "layer_health": [], "provider_health": [], "news_rows": [], "connected_assets": [], "source_register": [], "summary": {"source_status": "live/fresh"}},
            "summary": {}, "source_status": [], "unavailable": [], "errors": [], "caveats": [],
        }

    monkeypatch.setattr(backend_app, "get_map_news_event_fusion_payload", current_payload)
    client = TestClient(backend_app.app)
    first = client.post("/api/war-room-map-snapshots", json={"runtime_mode": "cache", "retention_days": 30})
    assert first.status_code == 200
    first_id = first.json()["data"]["active_snapshot"]["snapshot_id"]
    duplicate = client.post("/api/war-room-map-snapshots", json={"runtime_mode": "cache"})
    assert duplicate.json()["summary"]["capture_deduplicated"] is True

    marker_state.update(severity="elevated", second=True)
    second = client.post("/api/war-room-map-snapshots", json={"runtime_mode": "cache"})
    second_id = second.json()["data"]["active_snapshot"]["snapshot_id"]
    replay = client.get(f"/api/war-room-map-replay?time={second_id}&compareTo={first_id}")
    assert replay.status_code == 200
    assert replay.json()["data"]["diff"]["summary"]["added"] == 1
    assert client.get("/api/war-room-map-replay?time=../private.db").status_code == 422
