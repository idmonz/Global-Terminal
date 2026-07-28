from __future__ import annotations

from lib.coingecko_public_provider import build_coingecko_public_url, coingecko_rate_limit_status


def test_coingecko_keyless_fallback_is_rate_limited():
    url = build_coingecko_public_url(params={"vs_currency": "usd"})
    status = coingecko_rate_limit_status(now=10, last_request_at=9)
    assert "coingecko.com" in url
    assert status["rate_limited"] is True
