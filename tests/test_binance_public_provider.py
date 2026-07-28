from __future__ import annotations

from lib.binance_public_provider import build_binance_public_url


def test_binance_public_url_builder():
    url = build_binance_public_url(params={"symbol": "BTCUSDT"})
    assert "api.binance.com" in url
    assert "symbol=BTCUSDT" in url
