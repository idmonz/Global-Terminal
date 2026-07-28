from __future__ import annotations

from lib.api_contracts import API_CONTRACT_VERSION, build_api_market_intelligence_payload, validate_api_payload
from lib.market_intelligence import MARKET_INTELLIGENCE_VERSION, build_market_intelligence_contract
from scripts.export_api_fixtures import build_api_fixture_payloads


def test_market_intelligence_contract_builds_source_labeled_overview_and_charts():
    contract = build_market_intelligence_contract(include_runtime=False)

    assert contract["market_intelligence_version"] == MARKET_INTELLIGENCE_VERSION
    assert contract["workspace"] == "market-intelligence"
    assert len(contract["market_tape"]) >= 6
    assert len(contract["risk_heat"]) == len(contract["market_tape"])
    assert len(contract["market_heatmap"]) >= 20
    assert contract["chart_specs"]
    assert contract["provider_status"]
    assert contract["summary"]["heatmap_tile_count"] == len(contract["market_heatmap"])
    assert contract["summary"]["broker_execution_added"] is False
    assert contract["summary"]["non_advisory"] is True
    assert all(row["source_status"] for row in contract["market_tape"])
    assert all(row["not_financial_advice"] is True for row in contract["market_tape"])
    assert all(row["not_financial_advice"] is True for row in contract["risk_heat"])
    assert all(row["not_financial_advice"] is True for row in contract["market_heatmap"])
    assert all(row["source_status"] == "fixture" for row in contract["market_heatmap"])
    assert {"sector", "market_cap_weight", "daily_return_pct", "color_bucket"}.issubset(contract["market_heatmap"][0])
    assert all(row["not_financial_advice"] is True for row in contract["macro_context"])


def test_market_intelligence_api_payload_is_phase2b_json_safe():
    payload = build_api_market_intelligence_payload(include_runtime=False)

    assert payload["contract_version"] == API_CONTRACT_VERSION
    assert payload["payload_type"] == "market_intelligence"
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    assert payload["summary"]["workspace"] == "market-intelligence"
    assert payload["source_status"]
    assert "directional market advice" in " ".join(payload["caveats"])


def test_market_intelligence_fixture_is_exported_for_nextjs():
    payload = build_api_fixture_payloads()["market-intelligence.json"]

    assert payload["payload_type"] == "market_intelligence"
    assert payload["data"]["chart_specs"]
    assert payload["data"]["market_heatmap"]
    assert payload["data"]["market_tape"][0]["source_status"] == "fixture"
