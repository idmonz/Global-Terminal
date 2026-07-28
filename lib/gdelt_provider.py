from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests


BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def build_gdelt_doc_url(query: str, *, mode: str = "ArtList", max_records: int = 25, params: dict[str, Any] | None = None) -> str:
    query_params = {"query": query, "mode": mode, "format": "json", "maxrecords": max_records}
    query_params.update(params or {})
    return f"{BASE_URL}?{urlencode(query_params)}"


def fetch_gdelt_articles(query: str, *, session: Any | None = None, timeout: int = 15) -> dict[str, Any]:
    url = build_gdelt_doc_url(query)
    client = session or requests
    response = client.get(url, timeout=timeout)
    response.raise_for_status()
    return {"ok": True, "provider": "gdelt", "status": "available", "url": url, "data": response.json(), "caveat": "GDELT search is public and noisy; verify source freshness."}
