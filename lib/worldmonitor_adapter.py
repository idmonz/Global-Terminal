from __future__ import annotations

from typing import Any

import requests

from .config import get_settings
from .data_status import DataResult, error_result, ok_result


def _base_and_headers() -> tuple[str | None, dict[str, str], DataResult | None]:
    settings = get_settings()
    if not settings.world_monitor_base_url:
        return None, {}, error_result(source="WORLD_MONITOR_BASE_URL", provider="worldmonitor", error="WORLD_MONITOR_BASE_URL is not configured.")
    headers = {"Accept": "application/json"}
    if settings.world_monitor_key:
        headers["Authorization"] = f"Bearer {settings.world_monitor_key}"
    return settings.world_monitor_base_url.rstrip("/"), headers, None


def normalize_worldmonitor_response(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"items": data}
    return {"value": data}


def _request(endpoint: str, params: dict | None = None, timeout: int = 12) -> DataResult:
    base, headers, missing = _base_and_headers()
    if missing is not None:
        return missing
    try:
        response = requests.get(f"{base}/{endpoint.lstrip('/')}", headers=headers, params=params or {}, timeout=timeout)
        if response.status_code == 401:
            return error_result(source=f"{base}/{endpoint}", provider="worldmonitor", error="WorldMonitor API unavailable: key required.", is_paid_required=False)
        if response.status_code == 403:
            return error_result(source=f"{base}/{endpoint}", provider="worldmonitor", error="WorldMonitor API unavailable: key/subscription required.", is_paid_required=True)
        if response.status_code == 404:
            return error_result(source=f"{base}/{endpoint}", provider="worldmonitor", error="WorldMonitor endpoint absent or not public.")
        response.raise_for_status()
        data = normalize_worldmonitor_response(response.json())
        return ok_result(data, source=f"{base}/{endpoint}", provider="worldmonitor", coverage="adapter response")
    except requests.Timeout:
        return error_result(source=f"{base}/{endpoint}", provider="worldmonitor", error="WorldMonitor request timed out.")
    except ValueError:
        return error_result(source=f"{base}/{endpoint}", provider="worldmonitor", error="WorldMonitor response was not valid JSON.")
    except Exception as exc:
        return error_result(source=f"{base}/{endpoint}", provider="worldmonitor", error=str(exc))


def check_worldmonitor_status() -> DataResult:
    base, headers, missing = _base_and_headers()
    if missing is not None:
        return missing
    return _request("/health")


def worldmonitor_provider_center_status() -> dict[str, Any]:
    status = check_worldmonitor_status()
    return {
        "provider": "worldmonitor",
        "configured": status.ok or "not configured" not in str(status.error).lower(),
        "available": status.ok,
        "status": status.refreshed_status(),
        "warning": status.warning,
        "error": status.error,
        "caveat": "WorldMonitor is optional and reference-only; runtime code does not import external source.",
    }


def get_route_intelligence(fromIso2: str, toIso2: str, cargoType: str = "tanker", hs2: str = "27") -> DataResult:
    params = {"fromIso2": fromIso2, "toIso2": toIso2, "cargoType": cargoType, "hs2": hs2}
    return _request("/api/route-intelligence", params=params)


def get_public_panel_metadata() -> DataResult:
    return _request("/api/public/panels")


def get_supply_chain_chokepoints() -> DataResult:
    return _request("/api/supply-chain/chokepoints")


def get_hormuz_tracker_if_accessible() -> DataResult:
    return _request("/api/energy/hormuz")


def get_hormuz_tracker() -> DataResult:
    return get_hormuz_tracker_if_accessible()


def get_energy_panel_if_accessible() -> DataResult:
    return _request("/api/energy/panel")


def get_energy_crisis_policies() -> DataResult:
    return _request("/api/energy/crisis-policies")
