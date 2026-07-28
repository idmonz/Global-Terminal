from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests


BASE_URL = "https://api.binance.com"


def build_binance_public_url(endpoint: str = "/api/v3/ticker/24hr", params: dict[str, Any] | None = None) -> str:
    path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    query = urlencode(params or {})
    return f"{BASE_URL}{path}" + (f"?{query}" if query else "")


def fetch_binance_public(endpoint: str = "/api/v3/ticker/24hr", params: dict[str, Any] | None = None, *, session: Any | None = None, timeout: int = 15) -> dict[str, Any]:
    url = build_binance_public_url(endpoint, params)
    client = session or requests
    response = client.get(url, timeout=timeout)
    response.raise_for_status()
    return {"ok": True, "provider": "binance_public", "status": "available", "url": url, "data": response.json(), "caveat": "Exchange access and terms must be verified by the user."}
