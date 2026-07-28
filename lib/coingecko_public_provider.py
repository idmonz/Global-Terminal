from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlencode

import requests


BASE_URL = "https://api.coingecko.com/api/v3"
MIN_KEYLESS_INTERVAL_SECONDS = 6.0
_LAST_REQUEST_AT = 0.0


def get_coingecko_api_key() -> str | None:
    return os.getenv("COINGECKO_API_KEY") or None


def coingecko_rate_limit_status(now: float | None = None, last_request_at: float | None = None) -> dict[str, Any]:
    current = time.time() if now is None else now
    last = _LAST_REQUEST_AT if last_request_at is None else last_request_at
    wait = max(0.0, MIN_KEYLESS_INTERVAL_SECONDS - (current - last))
    return {"min_interval_seconds": MIN_KEYLESS_INTERVAL_SECONDS, "wait_seconds": round(wait, 2), "rate_limited": wait > 0}


def build_coingecko_public_url(endpoint: str = "/coins/markets", params: dict[str, Any] | None = None) -> str:
    path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    query = urlencode(params or {"vs_currency": "usd", "per_page": 50})
    return f"{BASE_URL}{path}" + (f"?{query}" if query else "")


def fetch_coingecko_public(endpoint: str = "/coins/markets", params: dict[str, Any] | None = None, *, session: Any | None = None, timeout: int = 15, enforce_rate_limit: bool = False) -> dict[str, Any]:
    global _LAST_REQUEST_AT
    url = build_coingecko_public_url(endpoint, params)
    key = get_coingecko_api_key()
    status = coingecko_rate_limit_status()
    if enforce_rate_limit and not key and status["rate_limited"]:
        return {"ok": False, "provider": "coingecko_public", "status": "rate_limited", "url": url, "data": None, "warning": "Keyless CoinGecko fallback is rate-limited."}
    headers = {"x-cg-demo-api-key": key} if key else {}
    client = session or requests
    response = client.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    _LAST_REQUEST_AT = time.time()
    return {"ok": True, "provider": "coingecko_public", "status": "configured" if key else "no_key_fallback", "url": url, "data": response.json(), "caveat": "Keyless fallback is rate-limited."}
