from __future__ import annotations

from lib.worldbank_provider import build_worldbank_indicator_url


def test_worldbank_url_builder():
    url = build_worldbank_indicator_url("KR", "NY.GDP.MKTP.CD")
    assert "/country/KR/indicator/NY.GDP.MKTP.CD" in url
    assert "format=json" in url
