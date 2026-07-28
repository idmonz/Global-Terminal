from __future__ import annotations

import os
from typing import Any

import requests


BASE_URL = "https://api.weather.gov"


def get_nws_user_agent() -> str | None:
    return os.getenv("NWS_USER_AGENT") or None


def build_nws_points_url(latitude: float, longitude: float) -> str:
    return f"{BASE_URL}/points/{latitude},{longitude}"


def fetch_nws_points(latitude: float, longitude: float, *, session: Any | None = None, user_agent: str | None = None, timeout: int = 15) -> dict[str, Any]:
    agent = user_agent or get_nws_user_agent()
    url = build_nws_points_url(latitude, longitude)
    if not agent:
        return {"ok": False, "provider": "nws", "status": "missing_key", "url": url, "data": None, "error": "NWS_USER_AGENT is required for NWS requests.", "caveat": "No secret value is displayed."}
    client = session or requests
    response = client.get(url, headers={"User-Agent": agent, "Accept": "application/geo+json"}, timeout=timeout)
    response.raise_for_status()
    return {"ok": True, "provider": "nws", "status": "available", "url": url, "data": response.json(), "caveat": "NWS data is official for supported US locations."}
