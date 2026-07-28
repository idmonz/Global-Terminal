from __future__ import annotations

import json

from lib.api_contracts import (
    build_api_financial_fundamentals_payload,
    build_api_options_quant_payload,
    build_api_screener_drilldown_payload,
    validate_api_payload,
)
from lib.web_market_workstations import (
    FINANCIAL_FUNDAMENTALS_VERSION,
    OPTIONS_QUANT_VERSION,
    SCREENER_DRILLDOWN_VERSION,
    build_financial_fundamentals_contract,
    build_options_quant_contract,
    build_screener_drilldown_contract,
)
from scripts.export_api_fixtures import build_api_fixture_payloads


def _assert_valid(payload: dict) -> None:
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    json.dumps(payload)


def test_financial_fundamentals_contract_is_dedicated_source_bound_and_non_advisory():
    contract = build_financial_fundamentals_contract("AAPL", include_runtime=False)

    assert contract["financial_fundamentals_version"] == FINANCIAL_FUNDAMENTALS_VERSION
    assert contract["workspace"] == "financial-fundamentals"
    assert contract["statement_metrics"]
    assert contract["valuation_quality"]
    assert contract["source_register"]
    assert contract["summary"]["broker_execution_added"] is False
    assert contract["summary"]["non_advisory"] is True
    assert all(row["not_financial_advice"] is True for row in contract["statement_metrics"])
    assert any(row.get("data_gap") for row in contract["source_register"])

    payload = build_api_financial_fundamentals_payload(symbol="AAPL", include_runtime=False)
    _assert_valid(payload)
    assert payload["payload_type"] == "financial_fundamentals"
    assert payload["summary"]["workspace"] == "financial-fundamentals"
    assert payload["source_status"]


def test_options_quant_contract_keeps_live_chain_gex_and_flow_provider_gated():
    contract = build_options_quant_contract("AAPL", include_runtime=False)

    assert contract["options_quant_version"] == OPTIONS_QUANT_VERSION
    assert contract["workspace"] == "options-quant"
    assert contract["provider_capabilities"]
    assert contract["greeks_table"]
    assert contract["scenario_table"]
    assert contract["readiness"]["manual_calculator_available"] is True
    assert contract["readiness"]["live_option_chain_claimed"] is False
    assert contract["readiness"]["gex_claimed"] is False
    assert contract["readiness"]["dealer_positioning_claimed"] is False
    assert contract["summary"]["broker_execution_added"] is False
    assert contract["summary"]["non_advisory"] is True
    assert any(row["source_status"] == "provider-required" for row in contract["source_register"])
    assert all(row.get("research_only") is True or row.get("not_financial_advice") is True for row in contract["greeks_table"])

    payload = build_api_options_quant_payload(symbol="AAPL", include_runtime=False)
    _assert_valid(payload)
    assert payload["payload_type"] == "options_quant"
    assert any(row.get("source_status") == "provider-required" for row in payload["unavailable"])


def test_screener_drilldown_contract_maps_heatmap_tiles_to_research_views():
    contract = build_screener_drilldown_contract(include_runtime=False)

    assert contract["screener_drilldown_version"] == SCREENER_DRILLDOWN_VERSION
    assert contract["workspace"] == "screener-drilldown"
    assert len(contract["drilldown_tiles"]) >= 20
    assert contract["sector_summaries"]
    assert contract["source_register"]
    assert contract["summary"]["broker_execution_added"] is False
    assert contract["summary"]["non_advisory"] is True
    assert any(row["target_view"] == "equity-intelligence" for row in contract["drilldown_tiles"])
    assert all(row["web_href"].startswith("/?view=") for row in contract["drilldown_tiles"])
    assert any(row["source_status"] == "provider-required" for row in contract["unavailable_sources"])

    payload = build_api_screener_drilldown_payload(include_runtime=False)
    _assert_valid(payload)
    assert payload["payload_type"] == "screener_drilldown"
    assert payload["summary"]["workspace"] == "screener-drilldown"


def test_phase5e3_fixtures_export_dedicated_workstation_payloads_without_secret_paths():
    payloads = build_api_fixture_payloads()
    encoded = json.dumps(payloads, sort_keys=True)

    assert payloads["financial-fundamentals.json"]["payload_type"] == "financial_fundamentals"
    assert payloads["options-quant.json"]["payload_type"] == "options_quant"
    assert payloads["screener-drilldown.json"]["payload_type"] == "screener_drilldown"
    assert payloads["financial-fundamentals.json"]["data"]["workspace"] == "financial-fundamentals"
    assert payloads["options-quant.json"]["data"]["readiness"]["live_option_chain_claimed"] is False
    assert payloads["screener-drilldown.json"]["data"]["drilldown_tiles"]
    assert "AIza" not in encoded
    assert "sk-" not in encoded
    assert ".env" not in encoded
    assert "\\data\\private\\" not in encoded
