from __future__ import annotations

from lib.endpoint_catalog import build_internal_endpoint_catalog, endpoint_openbb_candidates, validate_endpoint_request


def test_internal_catalog_includes_goal9_endpoint_families():
    catalog = build_internal_endpoint_catalog()

    for endpoint in ["price.history", "equity.financials.income", "rates.treasury_curve", "energy.petroleum_status", "shipping.chokepoint_info", "crypto.funding", "osint.events"]:
        assert endpoint in catalog


def test_endpoint_catalog_exposes_openbb_candidates():
    assert "equity.fundamental.income" in endpoint_openbb_candidates("equity.financials.income")


def test_endpoint_request_validation_requires_symbol():
    ok, issues = validate_endpoint_request({"endpoint": "equity.profile"})

    assert not ok
    assert "requires a symbol" in issues[0]
