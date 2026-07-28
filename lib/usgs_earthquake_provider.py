from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests


BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def build_usgs_earthquake_url(params: dict[str, Any] | None = None) -> str:
    query = {"format": "geojson", "limit": 100}
    query.update(params or {})
    return f"{BASE_URL}?{urlencode(query)}"


def fetch_usgs_earthquakes(params: dict[str, Any] | None = None, *, session: Any | None = None, timeout: int = 15) -> dict[str, Any]:
    url = build_usgs_earthquake_url(params)
    client = session or requests
    response = client.get(url, timeout=timeout)
    response.raise_for_status()
    return {"ok": True, "provider": "usgs_earthquake", "status": "available", "url": url, "data": response.json(), "caveat": "Event feeds can revise after initial publication."}
