from __future__ import annotations

from lib.api_contracts import API_CONTRACT_VERSION, build_api_crypto_intelligence_payload, validate_api_payload
from lib.crypto_intelligence_contract import CRYPTO_INTELLIGENCE_VERSION, build_crypto_intelligence_contract
from scripts.export_api_fixtures import build_api_fixture_payloads


def test_crypto_intelligence_contract_exposes_market_derivatives_scenarios_and_charts():
    contract = build_crypto_intelligence_contract("BTCUSDT", include_runtime=False)

    assert contract["crypto_intelligence_version"] == CRYPTO_INTELLIGENCE_VERSION
    assert contract["workspace"] == "crypto-intelligence"
    assert contract["symbol"] == "BTCUSDT"
    assert contract["market_overview"]["source_status"] == "fixture"
    assert contract["derivatives_snapshot"]["source_status"] == "fixture"
    assert contract["derivatives_timeseries"]
    assert contract["funding"]
    assert contract["open_interest"]
    assert contract["taker_flow"]
    assert contract["long_short_bias"]
    assert contract["liquidation_pressure_proxy"]
    assert contract["scenario_matrix"]
    assert contract["chart_specs"]
    assert contract["summary"]["broker_execution_added"] is False
    assert contract["summary"]["exchange_account_dependency_added"] is False
    assert contract["summary"]["non_advisory"] is True
    assert all(row["not_financial_advice"] is True for row in contract["derivatives_timeseries"])
    assert all(row["not_financial_advice"] is True for row in contract["liquidation_pressure_proxy"])
    assert all(row["not_financial_advice"] is True for row in contract["scenario_matrix"])


def test_crypto_intelligence_api_payload_is_phase2b_json_safe_and_free_first():
    payload = build_api_crypto_intelligence_payload(symbol="BTCUSDT", include_runtime=False)

    assert payload["contract_version"] == API_CONTRACT_VERSION
    assert payload["payload_type"] == "crypto_intelligence"
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    assert payload["summary"]["workspace"] == "crypto-intelligence"
    assert payload["summary"]["exchange_account_dependency_added"] is False
    assert payload["source_status"]
    assert any("public/free-first" in caveat for caveat in payload["caveats"])


def test_crypto_intelligence_fixture_is_exported_for_nextjs():
    payload = build_api_fixture_payloads()["crypto-intelligence.json"]

    assert payload["payload_type"] == "crypto_intelligence"
    assert payload["data"]["chart_specs"]
    assert payload["data"]["market_overview"]["not_financial_advice"] is True
