from __future__ import annotations

from lib.api_contracts import API_CONTRACT_VERSION, build_api_equity_intelligence_payload, validate_api_payload
from lib.equity_intelligence import EQUITY_INTELLIGENCE_VERSION, build_equity_intelligence_contract
from scripts.export_api_fixtures import build_api_fixture_payloads


def test_equity_intelligence_contract_exposes_stock_fundamental_options_and_chart_panels():
    contract = build_equity_intelligence_contract("AAPL", include_runtime=False)

    assert contract["equity_intelligence_version"] == EQUITY_INTELLIGENCE_VERSION
    assert contract["workspace"] == "equity-intelligence"
    assert contract["symbol"] == "AAPL"
    assert contract["price_history"]
    assert contract["technical_diagnostics"]["source_status"] == "fixture"
    assert contract["financial_overview"]["source_status"] == "fixture"
    assert contract["options_gamma_proxy"]["source_status"] == "provider-required"
    assert contract["scenario_matrix"]
    assert contract["chart_specs"]
    assert contract["provider_status"]
    assert contract["summary"]["broker_execution_added"] is False
    assert contract["summary"]["non_advisory"] is True
    assert all(row["not_financial_advice"] is True for row in contract["price_history"])
    assert all(row["not_financial_advice"] is True for row in contract["valuation_quality"])
    assert all(row["not_financial_advice"] is True for row in contract["scenario_matrix"])
    assert any(route["target_view"] == "options-quant" for route in contract["command_routes"])


def test_equity_intelligence_api_payload_keeps_provider_gaps_visible():
    payload = build_api_equity_intelligence_payload(symbol="AAPL", include_runtime=False)

    assert payload["contract_version"] == API_CONTRACT_VERSION
    assert payload["payload_type"] == "equity_intelligence"
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    assert payload["summary"]["workspace"] == "equity-intelligence"
    assert any(row.get("status") == "provider-required" for row in payload["unavailable"])
    assert any("Options/gamma" in caveat for caveat in payload["caveats"])


def test_equity_intelligence_fixture_remains_base_symbol_research_payload():
    payload = build_api_fixture_payloads()["equity-intelligence.json"]

    assert payload["payload_type"] == "equity_intelligence"
    assert payload["data"]["chart_specs"]
    assert payload["data"]["financial_overview"]["not_financial_advice"] is True
    assert payload["data"]["options_gamma_proxy"]["source_status"] == "provider-required"
