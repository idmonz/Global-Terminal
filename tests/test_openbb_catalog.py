from __future__ import annotations

from lib.openbb_catalog import build_openbb_capability_catalog, list_openbb_domains, list_openbb_required_keys, openbb_app_mapping_table


def test_openbb_catalog_has_required_domains_and_columns():
    catalog = build_openbb_capability_catalog()

    assert not catalog.empty
    assert {"Equity", "ETF", "Technical", "Quantitative"}.issubset(set(list_openbb_domains()))
    assert {"app_area", "openbb_domain", "openbb_endpoint_label", "requires_key", "native_fallback", "caveat"}.issubset(catalog.columns)


def test_openbb_required_keys_do_not_expose_values():
    keys = list_openbb_required_keys()

    assert "FMP_API_KEY" in set(keys["env_var"])
    assert "configured" in keys.columns
    assert "value" not in keys.columns


def test_openbb_app_mapping_table_includes_target_surfaces():
    mapping = openbb_app_mapping_table()

    assert {"Financial Terminal", "Portfolio Quant Lab", "Screener"}.issubset(set(mapping["app_area"]))
