from __future__ import annotations

from lib.no_key_provider_catalog import build_no_key_provider_table, classify_provider_access, list_no_key_providers


def test_no_key_provider_catalog_separates_access_models():
    providers = {item["provider_id"] for item in list_no_key_providers()}
    assert {"sec_edgar", "treasury_fiscal", "noaa_accessais", "coingecko_public"}.issubset(providers)
    assert classify_provider_access("opensky") == "oauth_optional"
    assert "historical_only" in set(build_no_key_provider_table()["status"])
