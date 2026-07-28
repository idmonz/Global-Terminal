from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests


BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"


def build_treasury_fiscal_url(endpoint: str = "v1/accounting/od/rates_of_exchange", params: dict[str, Any] | None = None) -> str:
    endpoint = endpoint.strip("/")
    query = urlencode(params or {"page[size]": 100}, doseq=True)
    return f"{BASE_URL}/{endpoint}" + (f"?{query}" if query else "")


def fetch_treasury_fiscal_data(endpoint: str = "v1/accounting/od/rates_of_exchange", params: dict[str, Any] | None = None, *, session: Any | None = None, timeout: int = 15) -> dict[str, Any]:
    url = build_treasury_fiscal_url(endpoint, params)
    client = session or requests
    response = client.get(url, timeout=timeout)
    response.raise_for_status()
    return {"ok": True, "provider": "treasury_fiscal", "status": "available", "url": url, "data": response.json(), "caveat": "Dataset schemas and update calendars vary by Treasury endpoint."}
