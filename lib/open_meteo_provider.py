from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests


BASE_URL = "https://api.open-meteo.com/v1/forecast"


def build_open_meteo_forecast_url(latitude: float, longitude: float, params: dict[str, Any] | None = None) -> str:
    query = {"latitude": latitude, "longitude": longitude, "hourly": "temperature_2m,precipitation,wind_speed_10m"}
    query.update(params or {})
    return f"{BASE_URL}?{urlencode(query, doseq=True)}"


def fetch_open_meteo_forecast(latitude: float, longitude: float, *, session: Any | None = None, timeout: int = 15) -> dict[str, Any]:
    url = build_open_meteo_forecast_url(latitude, longitude)
    client = session or requests
    response = client.get(url, timeout=timeout)
    response.raise_for_status()
    return {"ok": True, "provider": "open_meteo", "status": "available", "url": url, "data": response.json(), "caveat": "Forecast data is model-based and may update."}
