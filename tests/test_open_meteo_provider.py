from __future__ import annotations

from lib.open_meteo_provider import build_open_meteo_forecast_url


def test_open_meteo_url_builder():
    url = build_open_meteo_forecast_url(37.5, 127.0)
    assert "latitude=37.5" in url
    assert "longitude=127.0" in url
