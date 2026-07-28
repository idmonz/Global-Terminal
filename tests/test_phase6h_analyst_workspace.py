from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PANEL_IDS = {
    "chart-core",
    "technicals",
    "financials",
    "catalysts",
    "news",
    "sources",
    "comparison",
}


def test_workspace_manifest_is_compact_deterministic_and_exact():
    from lib.analyst_workspace import build_analyst_workspace_contract

    first = build_analyst_workspace_contract(
        "AAPL",
        asset_class="equity",
        interval="1d",
        range_name="3mo",
        runtime_mode="fixture",
    )
    second = build_analyst_workspace_contract(
        "AAPL",
        asset_class="equity",
        interval="1d",
        range_name="3mo",
        runtime_mode="fixture",
    )

    assert first == second
    assert first["workspace_version"] == "analyst_workspace.v1"
    assert first["identity"]["symbol"] == "AAPL"
    assert first["context"]["symbol"] == "AAPL"
    assert first["context"]["interval"] == "1d"
    assert first["context"]["range"] == "3mo"
    assert {panel["panel_id"] for panel in first["panels"]} == PANEL_IDS
    assert len(json.dumps(first, separators=(",", ":")).encode()) < 30_000
    assert "workstations" not in first
    assert "history" not in first
    assert "candles" not in json.dumps(first)


def test_panel_manifest_has_provenance_and_bounded_delivery_truth():
    from lib.analyst_workspace import build_analyst_workspace_contract

    workspace = build_analyst_workspace_contract(
        "AAPL",
        asset_class="equity",
        runtime_mode="fixture",
    )

    for panel in workspace["panels"]:
        assert panel["symbol"] == "AAPL"
        assert panel["endpoint"].startswith(
            "/api/symbol-workstation/AAPL/panels/"
        )
        assert panel["source_status"]
        assert "fetched_at" in panel
        assert "confidence" in panel
        assert "caveat" in panel
        assert "data_gap" in panel
        assert panel["cache_identity"].startswith("symbol-panel:AAPL:")

    plan = workspace["request_plan"]
    assert plan["initial_heavy_panel_count"] == 0
    assert plan["desktop_maximum_panel_requests"] == 4
    assert plan["mobile_initial_panel_requests"] == 1
    assert plan["hidden_mobile_panels_eagerly_fetched"] is False
    assert plan["concurrent_request_deduplication_required"] is True
    assert plan["same_symbol_lkg_required"] is True
    assert plan["broad_universe_fanout"] is False
    assert plan["watchlist_refresh_provider_call_ceiling"] == 16
    assert workspace["not_financial_advice"] is True


def test_unknown_symbol_never_substitutes_fixture_identity():
    from lib.analyst_workspace import build_analyst_workspace_contract

    workspace = build_analyst_workspace_contract(
        "NOTAREAL123",
        asset_class="equity",
        runtime_mode="fixture",
    )

    assert workspace["identity"]["symbol"] == "NOTAREAL123"
    assert workspace["readiness"]["status"] == "unavailable"
    assert workspace["panels"] == []
    encoded = json.dumps(workspace)
    assert "Apple" not in encoded
    assert '"AAPL"' not in encoded


@pytest.mark.parametrize(
    ("change_type", "expected"),
    [
        ("event", "catalysts"),
        ("news", "catalysts"),
        ("fundamental", "financials"),
        ("price", "chart-core"),
        ("performance", "chart-core"),
        ("source-status", "sources"),
        ("unknown", "chart-core"),
    ],
)
def test_change_type_maps_to_exact_panel(change_type: str, expected: str):
    from lib.analyst_workspace import map_change_type_to_panel

    assert map_change_type_to_panel(change_type) == expected


def test_change_context_is_exact_symbol_only():
    from lib.analyst_workspace import build_analyst_workspace_contract

    workspace = build_analyst_workspace_contract(
        "AAPL",
        runtime_mode="fixture",
        change_context={
            "change_id": "change_exact",
            "symbol": "AAPL",
            "change_type": "fundamental",
            "field": "eps",
            "before": 1.0,
            "after": 1.2,
            "source_url": "https://example.com/aapl",
        },
    )
    assert workspace["change_context"]["change_id"] == "change_exact"
    assert workspace["context"]["focused_panel"] == "financials"

    mismatch = build_analyst_workspace_contract(
        "AAPL",
        runtime_mode="fixture",
        change_context={
            "change_id": "change_wrong",
            "symbol": "MSFT",
            "change_type": "price",
        },
    )
    assert mismatch["change_context"]["status"] == "incompatible"
    assert mismatch["change_context"]["change_id"] is None
    assert mismatch["change_context"]["data_gap"]


def test_layout_and_return_state_are_bounded_and_private():
    from lib.analyst_workspace import (
        normalize_workspace_layout,
        sanitize_workspace_return_state,
    )

    layout = normalize_workspace_layout(
        {
            "preset": "research",
            "split_percent": 99,
            "focused_panel": "financials",
            "panel_order": ["financials", "chart-core", "bad", "financials"],
            "visible_panels": ["chart-core", "financials", "bad"],
            "private_note": "do not persist",
            "api_key": "secret",
        }
    )
    assert layout["split_percent"] == 72
    assert layout["panel_order"] == ["financials", "chart-core"]
    assert layout["visible_panels"] == ["chart-core", "financials"]
    assert "private_note" not in layout
    assert "api_key" not in layout

    state = sanitize_workspace_return_state(
        {
            "origin": "watchlist",
            "list": "daily",
            "change": "change_123",
            "severity": "material",
            "return": "javascript:alert(1)",
            "path": "C:\\Users\\private\\notes.txt",
            "token": "secret",
        }
    )
    assert state == {
        "origin": "watchlist",
        "list": "daily",
        "change": "change_123",
        "severity": "material",
    }


def test_workspace_api_etag_unknown_and_invalid_layout():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api.app import create_app

    client = TestClient(create_app())
    response = client.get(
        "/api/analyst-workspace/AAPL",
        params={
            "asset_class": "equity",
            "runtime_mode": "fixture",
            "interval": "1d",
            "range": "3mo",
        },
    )
    assert response.status_code == 200
    assert response.headers["etag"]
    assert len(response.content) < 30_000
    assert response.json()["payload_type"] == "analyst_workspace"

    conditional = client.get(
        "/api/analyst-workspace/AAPL",
        params={"runtime_mode": "fixture"},
        headers={"If-None-Match": response.headers["etag"]},
    )
    assert conditional.status_code == 304

    unknown = client.get(
        "/api/analyst-workspace/NOTAREAL123",
        params={"asset_class": "equity", "runtime_mode": "fixture"},
    )
    assert unknown.status_code == 404
    assert "Apple" not in unknown.text


def test_frontend_declares_dedupe_lkg_mobile_lazy_layout_and_keyboard_contracts():
    component = (
        ROOT / "apps" / "web" / "src" / "components" / "AnalystWorkspace.tsx"
    ).read_text(encoding="utf-8")
    page = (ROOT / "apps" / "web" / "src" / "app" / "page.tsx").read_text(
        encoding="utf-8"
    )

    assert "data-phase6h-analyst-workspace" in component
    assert "inflightPanelRequests" in component
    assert "last-known-good" in component
    assert "hidden_mobile_panels_eagerly_fetched" in component
    assert "localStorage" in component
    assert "global-terminal.analyst-layout.v1" in component
    assert "aria-label" in component
    assert "onKeyDown" in component
    assert 'requestedView === "analyst-workspace"' in page
    assert "loadCompactAnalystWorkspace" in page


def test_fixture_and_release_boundaries_include_contract_without_private_data():
    exporter = (ROOT / "scripts" / "export_api_fixtures.py").read_text(
        encoding="utf-8"
    )
    validator = (
        ROOT / "apps" / "web" / "scripts" / "validate-fixtures.mjs"
    ).read_text(encoding="utf-8")
    contracts = (
        ROOT / "apps" / "web" / "src" / "lib" / "contracts.ts"
    ).read_text(encoding="utf-8")

    assert '"analyst-workspace.json"' in exporter
    assert '"analyst-workspace.json"' in validator
    assert '"analyst-workspace"' in contracts
    assert '"analyst_workspace"' in contracts


def test_saved_primary_fixture_does_not_duplicate_chart_payload():
    from scripts.export_api_fixtures import build_api_fixture_payloads

    catalog = build_api_fixture_payloads()["analyst-workspace-primary-panels.json"]
    entry = catalog["data"]["primary_panels"][0]
    workstation = entry["data"]["workstations"][0]

    assert workstation["chart_views"]["price"]["candles"]
    assert workstation["chart_specs"] == []
    assert "capabilities" not in entry["data"]
