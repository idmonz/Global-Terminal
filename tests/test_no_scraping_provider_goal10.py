from __future__ import annotations

from lib.no_key_provider_catalog import list_no_key_providers


def test_goal10_does_not_register_forbidden_scraping_providers():
    provider_ids = " ".join(item["provider_id"].lower() for item in list_no_key_providers())
    assert "finviz" not in provider_ids
    assert "fincept" not in provider_ids
