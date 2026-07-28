from __future__ import annotations

from lib.usgs_earthquake_provider import build_usgs_earthquake_url


def test_usgs_earthquake_url_builder():
    url = build_usgs_earthquake_url({"minmagnitude": 5})
    assert "earthquake.usgs.gov" in url
    assert "minmagnitude=5" in url
