from __future__ import annotations

from lib.api_contracts import API_CONTRACT_VERSION, build_api_product_parity_payload, validate_api_payload
from lib.product_parity_inventory import PRODUCT_PARITY_INVENTORY_VERSION, build_product_parity_inventory


def test_product_parity_inventory_maps_streamlit_pages_to_phase5a_web_surfaces():
    inventory = build_product_parity_inventory()

    assert inventory["product_parity_inventory_version"] == PRODUCT_PARITY_INVENTORY_VERSION
    page_map = {row["page"]: row for row in inventory["streamlit_pages"]}
    assert page_map["pages/1_Market_Pulse.py"]["web_status"] == "phase5a-added"
    assert page_map["pages/2_Stock_Analyzer.py"]["web_status"] == "phase5a-added"
    assert page_map["pages/8_Crypto_Intelligence.py"]["web_status"] == "phase5a-added"
    assert page_map["pages/14_War_Room.py"]["web_status"] == "covered/phase5a-upgraded"
    assert page_map["pages/13_Screener.py"]["web_status"] == "missing"
    assert page_map["pages/16_Portfolio_Quant_Lab.py"]["web_status"] == "missing"
    assert all(row["source_status"] == "local/source-backed" for row in inventory["streamlit_pages"])


def test_product_parity_inventory_keeps_external_reference_boundary_explicit():
    inventory = build_product_parity_inventory()

    references = {row["external_project"]: row for row in inventory["external_reference_map"]}
    assert references["BB-Terminal"]["license_stance"] == "blocked/direct-copy-not-used"
    assert references["OpenBB"]["copied_source"] is False
    assert references["WorldMonitor"]["copied_source"] is False
    assert inventory["summary"]["external_source_copied"] is False
    assert inventory["summary"]["broker_execution_added"] is False
    assert inventory["summary"]["auth_billing_persistence_added"] is False
    assert inventory["summary"]["non_advisory"] is True


def test_product_parity_api_payload_is_phase2b_json_safe():
    payload = build_api_product_parity_payload()

    assert payload["contract_version"] == API_CONTRACT_VERSION
    assert payload["payload_type"] == "product_parity_inventory"
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    assert payload["source_status"]
    assert any(row["surface"] == "Dedicated screener workspace" for row in payload["unavailable"])
