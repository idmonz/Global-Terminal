from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests


def build_sdmx_url(base_url: str, flow: str, key: str = "all", params: dict[str, Any] | None = None) -> str:
    if not str(base_url).startswith(("https://", "http://")):
        raise ValueError("SDMX base_url must be http(s).")
    root = str(base_url).rstrip("/")
    path = f"{root}/data/{flow}/{key}"
    query = urlencode(params or {}, doseq=True)
    return f"{path}?{query}" if query else path


def fetch_sdmx_data(base_url: str, flow: str, key: str = "all", params: dict[str, Any] | None = None, *, session: Any | None = None, timeout: int = 15) -> dict[str, Any]:
    url = build_sdmx_url(base_url, flow, key, params)
    client = session or requests
    response = client.get(url, timeout=timeout)
    response.raise_for_status()
    return {"ok": True, "provider": "sdmx", "status": "available", "url": url, "data": response.text, "caveat": "SDMX schemas differ by statistical agency."}
