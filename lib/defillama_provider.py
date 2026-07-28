from __future__ import annotations

from typing import Any

import requests


BASE_URL = "https://api.llama.fi"


def build_defillama_url(endpoint: str = "/protocols") -> str:
    path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    return f"{BASE_URL}{path}"


def fetch_defillama(endpoint: str = "/protocols", *, session: Any | None = None, timeout: int = 15) -> dict[str, Any]:
    url = build_defillama_url(endpoint)
    client = session or requests
    response = client.get(url, timeout=timeout)
    response.raise_for_status()
    return {"ok": True, "provider": "defillama", "status": "available", "url": url, "data": response.json(), "caveat": "Public DeFi datasets require methodology review."}
