from __future__ import annotations

from lib.noaa_accessais_provider import build_noaa_accessais_metadata, fetch_noaa_accessais_catalog


def test_noaa_accessais_is_historical_only():
    metadata = build_noaa_accessais_metadata()
    result = fetch_noaa_accessais_catalog()
    assert metadata["status"] == "historical_only"
    assert result["status"] == "historical_only"
    assert "live" in result["caveat"].lower()
