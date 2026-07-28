from __future__ import annotations

import json
import re
from pathlib import Path

from backend.api import app as backend_app
from lib.api_contracts import API_CONTRACT_VERSION, build_api_command_workspace_payload, validate_api_payload
from lib.command_workspace import COMMAND_WORKSPACE_VERSION, build_command_workspace_contract
from lib.event_asset_graph import build_event_asset_graph_contract
from scripts.export_api_fixtures import build_api_fixture_payloads, export_api_fixtures


EXPECTED_COMMANDS = {"NI", "MAP", "DES", "FA", "GP", "HP", "WEI", "CURV", "FXC", "CRYPTO", "OMON"}
FORBIDDEN_RESULT_PHRASES = [
    r"\bshould\s+buy\b",
    r"\bshould\s+sell\b",
    r"\bshould\s+hold\b",
    r"\bbuy\s+recommendation\b",
    r"\bsell\s+recommendation\b",
    r"\bhold\s+recommendation\b",
    r"\bexecute\s+order\b",
    r"\bbroker\s+execution\b",
    r"\border\s+routing\b",
]


def _event_row(**overrides):
    row = {
        "event_id": "evt-red-sea-phase3",
        "timestamp": "2026-06-16T00:00:00+00:00",
        "title": "Red Sea shipping risk keeps oil and FX context elevated",
        "summary": "Public feed row linking shipping, oil, global trade, FX risk, and command routing.",
        "domain": "chokepoints",
        "severity": "high",
        "region": "Red Sea",
        "source": "phase3.fixture",
        "source_url": "https://example.test/phase-3/red-sea",
        "provider": "fixture",
        "fetched_at": "2026-06-16T00:00:00+00:00",
        "freshness": "fixture",
        "source_status": "fixture",
        "confidence": 0.62,
        "related_tickers": ["CL=F", "BZ=F"],
        "coordinate_method": "fixture_coordinates",
        "data_gap": "No live AIS or vessel-flow provider in this fixture.",
        "caveat": "Static fixture row; not live vessel tracking.",
    }
    row.update(overrides)
    return row


def _crypto_event_row(**overrides):
    row = _event_row(
        event_id="evt-crypto-phase3",
        title="Bitcoin liquidity context updates after public crypto feed refresh",
        summary="Public crypto row linking bitcoin, CoinGecko, Binance, and command routing.",
        domain="crypto",
        region="Global",
        related_tickers=["BTC"],
    )
    row.update(overrides)
    return row


def _provider_row(**overrides):
    row = {
        "provider": "opensky",
        "source": "OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET",
        "status": "missing-key",
        "availability": "unavailable",
        "row_count": 0,
        "fetched_at": None,
        "warning": "OpenSky remains unavailable until OAuth credentials and state-vector fetch succeed.",
        "error": "Missing optional provider credentials.",
        "recommended_action": "Keep flight layer unavailable.",
        "caveat": "No fake live flight tracking is exported.",
    }
    row.update(overrides)
    return row


def _graph(events=None, providers=None):
    return build_event_asset_graph_contract(events=events or [_event_row()], provider_rows=providers or [_provider_row()])


def _encoded(value) -> str:
    return json.dumps(value, sort_keys=True)


def test_command_workspace_contract_reuses_phase2f_graph_command_suggestions():
    graph = _graph()
    workspace = build_command_workspace_contract(event_graph=graph, provider_rows=[_provider_row()])

    assert workspace["command_workspace_version"] == COMMAND_WORKSPACE_VERSION
    assert {row["command"] for row in workspace["commands"]} == EXPECTED_COMMANDS
    assert {row["command"] for row in workspace["command_results"]} == EXPECTED_COMMANDS
    assert any(ctx["source"] == "phase2f_event_asset_graph" and ctx["command"] == "NI" for ctx in workspace["contexts"])
    assert any(ctx["context_type"] == "event" for ctx in workspace["contexts"])
    assert workspace["summary"]["phase2f_command_suggestion_count"] >= 1
    assert workspace["summary"]["broker_execution_added"] is False
    assert workspace["summary"]["hosted_persistence_added"] is False


def test_command_records_carry_source_provider_caveat_and_gap_fields():
    workspace = build_command_workspace_contract(event_graph=_graph(), provider_rows=[_provider_row()])
    required_fields = {
        "command",
        "label",
        "description",
        "accepted_context_types",
        "provider",
        "source_status",
        "freshness",
        "implementation_status",
        "requires_provider",
        "result_status",
        "caveat",
        "data_gap",
        "not_financial_advice",
    }

    assert workspace["commands"]
    assert all(required_fields.issubset(command) for command in workspace["commands"])
    assert all(command["not_financial_advice"] is True for command in workspace["commands"])
    assert all(command["caveat"] for command in workspace["commands"])
    assert all(command["data_gap"] for command in workspace["commands"])


def test_provider_required_commands_are_unavailable_when_live_providers_are_missing():
    workspace = build_command_workspace_contract(event_graph=_graph(), provider_rows=[_provider_row()])
    results = {row["command"]: row for row in workspace["command_results"]}

    for command in ["DES", "FA", "GP", "HP", "WEI", "CURV", "FXC", "CRYPTO", "OMON"]:
        assert results[command]["available"] is False
        assert results[command]["result_status"] in {"provider-required", "missing-key", "unavailable"}
        assert results[command]["provider_requirement"]["status"] in {"missing-key", "unavailable", "provider-required"}
        assert results[command]["data_gap"]

    assert results["MAP"]["result_status"] == "proxy/static"
    assert results["MAP"]["available"] is False
    assert results["NI"]["result_status"] in {"source-backed-preview", "provider-required"}


def test_phase5a_commands_open_read_only_workstation_routes_without_live_claims():
    workspace = build_command_workspace_contract(event_graph=_graph(), provider_rows=[_provider_row()])
    results = {row["command"]: row for row in workspace["command_results"]}

    expected_routes = {
        "NI": ("/api/market-intelligence", "market-intelligence"),
        "MAP": ("/api/war-room-map", "war-room-map"),
        "FA": ("/api/equity-intelligence", "equity-intelligence"),
        "DES": ("/api/equity-intelligence", "financial-fundamentals"),
        "OMON": ("/api/equity-intelligence", "options-quant"),
        "CRYPTO": ("/api/crypto-intelligence", "crypto-intelligence"),
    }

    for command, (route, workspace_view) in expected_routes.items():
        result = results[command]
        assert result["route"] == route
        assert result["workspace_view"] == workspace_view
        assert result["available"] is False
        assert result["action_contract"]["enabled"] is True
        assert result["action_contract"]["broker_execution"] is False
        assert result["action_contract"]["market_action_routing"] is False
        assert result["action_contract"]["non_advisory"] is True


def test_live_crypto_provider_evidence_gates_crypto_command_available_without_broker_actions():
    providers = [
        _provider_row(
            provider="coingecko",
            source="CoinGecko public markets",
            status="live/fresh",
            availability="available",
            row_count=2,
            fetched_at="2026-06-16T00:00:00+00:00",
            error=None,
            paid_required=False,
            warning=None,
            caveat="Public market data only; no exchange account or broker path.",
        )
    ]
    graph = _graph(events=[_crypto_event_row(source_status="live/fresh", provider="coingecko")], providers=providers)
    workspace = build_command_workspace_contract(event_graph=graph, provider_rows=providers)
    crypto_result = next(row for row in workspace["command_results"] if row["command"] == "CRYPTO")

    assert crypto_result["available"] is True
    assert crypto_result["result_status"] == "available"
    assert crypto_result["provider_requirement"]["provider"] == "coingecko"
    assert crypto_result["action_contract"]["broker_execution"] is False
    assert crypto_result["action_contract"]["market_action_routing"] is False


def test_command_workspace_api_payload_is_phase2b_json_safe_and_non_advisory():
    payload = build_api_command_workspace_payload(event_graph=_graph(), provider_rows=[_provider_row()])

    assert payload["contract_version"] == API_CONTRACT_VERSION
    assert payload["payload_type"] == "command_workspace"
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    encoded = _encoded(payload).lower()
    for phrase in FORBIDDEN_RESULT_PHRASES:
        assert not re.search(phrase, encoded), phrase


def test_fixture_export_includes_command_workspace_and_keeps_missing_live_providers_explicit(tmp_path):
    payloads = build_api_fixture_payloads()
    written = export_api_fixtures(tmp_path)

    assert "command-workspace.json" in payloads
    assert "command-workspace.json" in {path.name for path in written}
    fixture = payloads["command-workspace.json"]
    assert fixture["payload_type"] == "command_workspace"
    assert fixture["summary"]["available_command_count"] == 0
    assert fixture["summary"]["provider_required_command_count"] >= 1
    assert any(row["capability"] == "broker_execution" for row in fixture["unavailable"])
    valid, issues = validate_api_payload(fixture)
    assert valid, issues


def test_backend_optional_command_workspace_getter_is_valid():
    payload = backend_app.get_command_workspace_payload()

    assert payload["payload_type"] == "command_workspace"
    valid, issues = validate_api_payload(payload)
    assert valid, issues


def test_web_fixture_validator_knows_command_workspace_fixture():
    validator = Path("apps/web/scripts/validate-fixtures.mjs").read_text(encoding="utf-8")

    assert "command-workspace.json" in validator
    assert "command_workspace" in validator
