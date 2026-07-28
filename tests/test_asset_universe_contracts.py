from __future__ import annotations

import json

from lib.api_contracts import API_CONTRACT_VERSION, build_api_asset_universe_payload, validate_api_payload
from lib.asset_universe import build_asset_universe_contract


def test_asset_universe_contract_defines_expected_asset_classes_without_rows():
    payload = build_asset_universe_contract()
    asset_classes = payload["asset_classes"]

    assert {row["asset_class"] for row in asset_classes} == {
        "equity",
        "etf",
        "fund",
        "index",
        "fx_pair",
        "crypto_pair",
        "money_market",
    }
    assert payload["readiness"]["schema_ready"] is True
    assert payload["readiness"]["live_rows_claimed"] is False
    assert payload["readiness"]["external_rows_copied"] is False
    assert payload["reference_sources"][0]["project"] == "FinanceDatabase"
    assert payload["reference_sources"][0]["license_stance"] == "direct-use-allowed"
    assert all(row["source_status"] == "reference-schema" for row in asset_classes)
    assert all(row["live_rows_claimed"] is False for row in asset_classes)


def test_asset_universe_api_payload_is_json_safe_and_honest_about_availability():
    payload = build_api_asset_universe_payload()

    assert payload["contract_version"] == API_CONTRACT_VERSION
    assert payload["payload_type"] == "asset_universe"
    assert payload["summary"]["asset_class_count"] == 7
    assert payload["summary"]["live_rows_claimed"] is False
    assert payload["summary"]["external_rows_copied"] is False
    assert payload["unavailable"]
    assert all(row["availability"] == "limited" for row in payload["unavailable"])
    assert any(row["provider"] == "phase2e_native_contract" for row in payload["source_status"])

    valid, issues = validate_api_payload(payload)
    assert valid, issues
    encoded = json.dumps(payload, sort_keys=True)
    assert "FinanceDatabase-main/database/equities/NMS.csv:1-1" in encoded
    assert "AAPL" not in encoded
