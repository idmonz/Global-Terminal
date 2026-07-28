from __future__ import annotations

import json

from lib.api_contracts import API_CONTRACT_VERSION, validate_api_payload
from scripts.export_api_fixtures import FIXTURE_TIMESTAMP, build_api_fixture_payloads, export_api_fixtures


EXPECTED_FIXTURES = {
    "product-parity.json",
    "market-intelligence.json",
    "equity-intelligence.json",
    "financial-fundamentals.json",
    "options-quant.json",
    "portfolio-risk.json",
    "research-memory.json",
    "daily-brief.json",
    "screener-drilldown.json",
    "market-map-screener.json",
    "crypto-intelligence.json",
    "symbol-directory.json",
    "symbol-workstation.json",
    "symbol-workstation-summaries.json",
    "analyst-workspace.json",
    "analyst-workspace-catalog.json",
    "analyst-workspace-primary-panels.json",
    "watchlist-desk.json",
    "watchlist-alert-manager.json",
    "hosted-scheduler-operations.json",
    "attention-desk.json",
    "feeds.json",
    "provider-health.json",
    "layers.json",
    "news.json",
    "war-room.json",
    "war-room-map.json",
    "map-news-event-fusion.json",
    "war-room-map-replay.json",
    "ai-providers.json",
    "asset-universe.json",
    "event-asset-graph.json",
    "command-workspace.json",
    "research-report.json",
    "manifest.json",
}


def _encoded(payloads: dict[str, dict]) -> str:
    return json.dumps(payloads, sort_keys=True)


def test_fixture_payloads_are_deterministic_json_safe_and_key_masked(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_local_secret_value_should_not_export")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-local-secret")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "opensky-local-secret")
    monkeypatch.setenv("OPENSKY_CLIENT_ID", "opensky-client")

    first = build_api_fixture_payloads()
    second = build_api_fixture_payloads()
    encoded = _encoded(first)

    assert set(first) == EXPECTED_FIXTURES
    assert first == second
    assert "AIza_local_secret_value_should_not_export" not in encoded
    assert "sk-ant-local-secret" not in encoded
    assert "opensky-local-secret" not in encoded
    assert "OPENSKY_CLIENT_SECRET" in encoded
    assert "\\data\\private\\" not in encoded
    assert ".env" not in encoded

    for payload in first.values():
        assert payload["contract_version"] == API_CONTRACT_VERSION
        assert payload["generated_at"] == FIXTURE_TIMESTAMP
        valid, issues = validate_api_payload(payload)
        assert valid, issues
        json.dumps(payload)


def test_export_api_fixtures_writes_expected_files(tmp_path):
    written = export_api_fixtures(tmp_path)

    assert {path.name for path in written} == EXPECTED_FIXTURES
    for path in written:
        payload = json.loads(path.read_text(encoding="utf-8"))
        valid, issues = validate_api_payload(payload)
        assert valid, issues
        assert payload["generated_at"] == FIXTURE_TIMESTAMP


def test_fixture_payloads_keep_optional_providers_unavailable_without_fake_live():
    payloads = build_api_fixture_payloads()

    layer_rows = payloads["layers.json"]["data"]["layers"]
    flight = next(row for row in layer_rows if row["layer_id"] == "flight_tracking_unavailable")
    provider_rows = payloads["provider-health.json"]["data"]

    assert flight["availability"] == "unavailable"
    assert flight["row_count"] == 0
    assert any(row["provider"] == "opensky" and row["status"] == "missing-key" for row in provider_rows)
    assert "fixture" in payloads["news.json"]["summary"]["status"] or payloads["news.json"]["summary"]["status"] == "available"


def test_asset_universe_fixture_is_reference_schema_not_live_rows():
    payload = build_api_fixture_payloads()["asset-universe.json"]

    assert payload["payload_type"] == "asset_universe"
    assert payload["summary"]["reference_project"] == "FinanceDatabase"
    assert payload["summary"]["external_rows_copied"] is False
    assert payload["summary"]["live_rows_claimed"] is False
    assert all(row["live_rows_claimed"] is False for row in payload["data"]["asset_classes"])
    assert any(row["asset_class"] == "equity" for row in payload["data"]["asset_classes"])


def test_event_asset_graph_fixture_keeps_live_persistence_unavailable():
    payload = build_api_fixture_payloads()["event-asset-graph.json"]

    assert payload["payload_type"] == "event_asset_graph"
    assert payload["summary"]["persistence_status"] == "unavailable"
    assert payload["summary"]["live_graph_persistence"] is False
    assert payload["data"]["readiness"]["graph_database_dependency_added"] is False
    assert any(row["capability"] == "live_graph_persistence" for row in payload["unavailable"])


def test_command_workspace_fixture_keeps_provider_required_commands_unavailable():
    payload = build_api_fixture_payloads()["command-workspace.json"]

    assert payload["payload_type"] == "command_workspace"
    assert payload["summary"]["available_command_count"] == 0
    assert payload["summary"]["provider_required_command_count"] >= 1
    assert any(row["command"] == "CRYPTO" and row["result_status"] == "provider-required" for row in payload["data"]["command_results"])
    assert any(row["capability"] == "broker_execution" for row in payload["unavailable"])


def test_war_room_map_fixture_labels_coordinates_and_provider_gates_live_layers():
    payload = build_api_fixture_payloads()["war-room-map.json"]

    assert payload["payload_type"] == "war_room_map"
    assert payload["summary"]["marker_count"] >= 1
    assert payload["summary"]["live_ais_claimed"] is False
    assert payload["summary"]["live_flight_tracking_claimed"] is False
    assert payload["summary"]["live_sanctions_claimed"] is False
    assert all(row["coordinate_status"] in {"source-backed", "fixture", "static/proxy", "approximate"} for row in payload["data"]["markers"])
    assert any(row["availability"] == "unavailable" for row in payload["data"]["layers"])
    assert any(row["window_id"] == "saved_compare_session" and row["available"] is False for row in payload["data"]["compare_windows"])


def test_war_room_map_replay_fixture_is_fictional_and_does_not_read_local_history():
    payload = build_api_fixture_payloads()["war-room-map-replay.json"]

    assert payload["payload_type"] == "war_room_map_replay"
    assert payload["summary"]["historical_truth"] == "fictional-demo"
    assert payload["data"]["privacy_scope"] == "deterministic-public-fixture"
    assert payload["data"]["readiness"]["capture_available"] is False
    assert all(row["source_status"] == "fixture" for row in payload["data"]["snapshots"])


def test_phase5a_workstation_fixtures_are_source_labeled_and_non_advisory():
    payloads = build_api_fixture_payloads()
    expected = {
        "product-parity.json": "product_parity_inventory",
        "market-intelligence.json": "market_intelligence",
        "equity-intelligence.json": "equity_intelligence",
        "crypto-intelligence.json": "crypto_intelligence",
    }

    for fixture_name, payload_type in expected.items():
        payload = payloads[fixture_name]
        assert payload["payload_type"] == payload_type
        assert payload["summary"]["non_advisory"] is True
        assert payload["source_status"]
        assert payload["caveats"]

    assert payloads["market-intelligence.json"]["data"]["chart_specs"]
    assert payloads["equity-intelligence.json"]["data"]["chart_specs"]
    assert payloads["crypto-intelligence.json"]["data"]["chart_specs"]
    assert all(row["not_financial_advice"] is True for row in payloads["market-intelligence.json"]["data"]["market_tape"])

def test_research_report_fixture_is_source_bound_and_non_advisory():
    payload = build_api_fixture_payloads()["research-report.json"]
    encoded = json.dumps(payload, sort_keys=True).lower()

    assert payload["payload_type"] == "research_report"
    assert payload["summary"]["non_advisory"] is True
    assert payload["summary"]["section_count"] >= 8
    assert payload["data"]["sections"]
    assert payload["data"]["source_register"]
    assert payload["data"]["policy"]["account_action_enabled"] is False
    assert payload["data"]["policy"]["broker_or_order_path_enabled"] is False
    assert payload["data"]["policy"]["forbidden_language_detected"] == []
    for phrase in [
        "trade permission",
        "recommended leverage",
        "maximum leverage",
        "long entry",
        "short entry",
        "entry zone",
        "stop loss",
        "take profit",
        "position size",
        "final action",
        "broker execution",
        "order routing",
    ]:
        assert phrase not in encoded
    assert all(section["not_financial_advice"] is True for section in payload["data"]["sections"])
    assert all(row["not_financial_advice"] is True for row in payload["data"]["scenario_matrix"])
