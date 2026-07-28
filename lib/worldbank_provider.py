from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests


BASE_URL = "https://api.worldbank.org/v2"


def build_worldbank_indicator_url(country: str = "US", indicator: str = "NY.GDP.MKTP.CD", params: dict[str, Any] | None = None) -> str:
    query = {"format": "json", "per_page": 100}
    query.update(params or {})
    return f"{BASE_URL}/country/{country}/indicator/{indicator}?{urlencode(query)}"


def fetch_worldbank_indicator(country: str = "US", indicator: str = "NY.GDP.MKTP.CD", *, session: Any | None = None, timeout: int = 15) -> dict[str, Any]:
    url = build_worldbank_indicator_url(country, indicator)
    client = session or requests
    response = client.get(url, timeout=timeout)
    response.raise_for_status()
    return {"ok": True, "provider": "worldbank", "status": "available", "url": url, "data": response.json(), "caveat": "Official country indicators may be revised or lagged."}
