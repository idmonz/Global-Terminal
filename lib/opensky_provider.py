from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .data_status import DataResult, error_result, ok_result
from .env_loader import get_env_var
from .runtime_cache import fetch_json_with_cache

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


OPENSKY_API_BASE_URL = "https://opensky-network.org/api"
OPENSKY_STATES_URL = f"{OPENSKY_API_BASE_URL}/states/all"
OPENSKY_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

STATE_VECTOR_FIELDS = [
    "icao24",
    "callsign",
    "origin_country",
    "time_position",
    "last_contact",
    "lon",
    "lat",
    "baro_altitude_m",
    "on_ground",
    "velocity_mps",
    "true_track_deg",
    "vertical_rate_mps",
    "sensors",
    "geo_altitude_m",
    "squawk",
    "spi",
    "position_source",
    "category",
]

POSITION_SOURCE_LABELS = {
    0: "ads-b",
    1: "asterix",
    2: "mlat",
    3: "flarm",
}

CATEGORY_LABELS = {
    0: "no_information",
    1: "no_adsb_emitter_category",
    2: "light",
    3: "small",
    4: "large",
    5: "high_vortex_large",
    6: "heavy",
    7: "high_performance",
    8: "rotorcraft",
    9: "glider",
    10: "lighter_than_air",
    11: "parachutist",
    12: "ultralight",
    13: "reserved",
    14: "unmanned_aerial_vehicle",
    15: "space_or_transatmospheric",
    16: "surface_emergency_vehicle",
    17: "surface_service_vehicle",
    18: "point_obstacle",
    19: "cluster_obstacle",
    20: "line_obstacle",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _timestamp(value: Any) -> str | None:
    try:
        if value is None:
            return None
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except Exception:
        return None


def _configured_credentials(client_id: str | None = None, client_secret: str | None = None) -> tuple[str | None, str | None]:
    return client_id or get_env_var("OPENSKY_CLIENT_ID"), client_secret or get_env_var("OPENSKY_CLIENT_SECRET")


def opensky_credentials_configured() -> bool:
    client_id, client_secret = _configured_credentials()
    return bool(client_id and client_secret)


def build_opensky_optional_status() -> dict[str, Any]:
    configured = opensky_credentials_configured()
    return {
        "provider": "opensky",
        "configured": configured,
        "available": configured,
        "status": "configured" if configured else "unavailable",
        "auth_mode": "oauth2_client_credentials" if configured else "missing_oauth2_client_credentials",
        "warning": None
        if configured
        else "Live flight tracking unavailable. Add OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET to enable an authenticated probe.",
        "caveat": "OpenSky /states/all is displayed only after credentials exist and a fetch succeeds.",
    }


def fetch_opensky_access_token(
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    session: Any | None = None,
    timeout: int = 10,
) -> tuple[str | None, DataResult]:
    """Fetch an OpenSky OAuth2 token without storing the secret or token in status data."""
    resolved_id, resolved_secret = _configured_credentials(client_id, client_secret)
    if not resolved_id or not resolved_secret:
        return None, error_result(
            source="OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET",
            provider="opensky",
            error="Missing optional environment variable: OPENSKY_CLIENT_ID or OPENSKY_CLIENT_SECRET",
            warning="OpenSky authenticated flight tracking is disabled until OAuth2 client credentials are configured.",
            is_paid_required=True,
            coverage="missing key",
        )
    if requests is None and session is None:
        return None, error_result(source=OPENSKY_TOKEN_URL, provider="opensky", error="requests is not installed")

    client = session or requests
    try:
        response = client.post(
            OPENSKY_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": resolved_id,
                "client_secret": resolved_secret,
            },
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        status_code = getattr(response, "status_code", None)
        if status_code in {401, 403}:
            raise PermissionError(f"{status_code} OpenSky OAuth credential rejected")
        if status_code == 429:
            raise RuntimeError("429 OpenSky OAuth rate limited")
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not token:
            raise RuntimeError("OpenSky OAuth response did not include access_token")
        return token, ok_result(
            {"token_type": payload.get("token_type"), "expires_in": payload.get("expires_in")},
            source=OPENSKY_TOKEN_URL,
            provider="opensky_oauth",
            coverage="token acquired",
            stale_after_seconds=int(payload.get("expires_in") or 1800),
        )
    except Exception as exc:
        return None, error_result(source=OPENSKY_TOKEN_URL, provider="opensky", error=str(exc), coverage="oauth error")


def build_opensky_states_params(
    *,
    time: int | None = None,
    icao24: str | list[str] | None = None,
    bounds: dict[str, float] | tuple[float, float, float, float] | None = None,
    extended: bool = False,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if time is not None:
        params["time"] = int(time)
    if icao24:
        items = [icao24] if isinstance(icao24, str) else list(icao24)
        params["icao24"] = [str(item).strip().lower() for item in items if str(item).strip()]
    if bounds:
        if isinstance(bounds, dict):
            required = ["lamin", "lomin", "lamax", "lomax"]
            if not all(key in bounds for key in required):
                raise ValueError("bounds dict must contain lamin, lomin, lamax, lomax")
            params.update({key: float(bounds[key]) for key in required})
        else:
            lamin, lomin, lamax, lomax = bounds
            params.update({"lamin": float(lamin), "lomin": float(lomin), "lamax": float(lamax), "lomax": float(lomax)})
    if extended:
        params["extended"] = 1
    return params


def _cache_key(params: dict[str, Any], *, auth_mode: str) -> str:
    return "opensky:states:" + auth_mode + ":" + json.dumps(params, sort_keys=True, default=str)


def _normalize_state_vector(vector: list[Any], *, response_time: Any, status: DataResult) -> dict[str, Any]:
    padded = list(vector) + [None] * max(0, len(STATE_VECTOR_FIELDS) - len(vector))
    base = dict(zip(STATE_VECTOR_FIELDS, padded[: len(STATE_VECTOR_FIELDS)]))
    callsign = str(base.get("callsign") or "").strip()
    icao24 = str(base.get("icao24") or "").strip().lower()
    lat = _safe_float(base.get("lat"))
    lon = _safe_float(base.get("lon"))
    velocity_mps = _safe_float(base.get("velocity_mps"))
    velocity_kts = velocity_mps * 1.943844 if velocity_mps is not None else None
    fetched_at = status.fetched_at.isoformat()
    source_status = status.refreshed_status()
    coordinate_method = "opensky_state_vector" if lat is not None and lon is not None else "unmapped"
    gaps: list[str] = []
    if not callsign:
        gaps.append("OpenSky state vector missing callsign.")
    if lat is None or lon is None:
        gaps.append("OpenSky state vector missing WGS84 coordinates.")
    position_source = _safe_int(base.get("position_source"))
    category = _safe_int(base.get("category"))
    label = callsign or icao24 or "aircraft"
    return {
        **base,
        "callsign": callsign,
        "icao24": icao24,
        "time_position_iso": _timestamp(base.get("time_position")),
        "last_contact_iso": _timestamp(base.get("last_contact")),
        "response_time": response_time,
        "response_time_iso": _timestamp(response_time),
        "lat": lat,
        "lon": lon,
        "velocity_kts": velocity_kts,
        "position_source_label": POSITION_SOURCE_LABELS.get(position_source, "unknown"),
        "category_label": CATEGORY_LABELS.get(category, "unknown"),
        "title": f"{label} OpenSky aircraft state",
        "summary": f"{base.get('origin_country') or 'Unknown origin'} aircraft state vector from OpenSky.",
        "timestamp": _timestamp(base.get("last_contact")) or _timestamp(response_time) or _now_iso(),
        "domain": "flight",
        "region": base.get("origin_country") or "Global",
        "source": "OpenSky Network",
        "source_url": OPENSKY_STATES_URL,
        "url": OPENSKY_STATES_URL,
        "provider": "opensky",
        "credibility": "official/public",
        "confidence": 0.82 if coordinate_method == "opensky_state_vector" else 0.45,
        "coordinate_method": coordinate_method,
        "fetched_at": fetched_at,
        "freshness": source_status,
        "source_status": source_status,
        "data_gap": "; ".join(gaps),
        "caveat": "OpenSky state vectors can be delayed, rate-limited, incomplete, or restricted by terms.",
    }


def normalize_opensky_states(payload: Any, status: DataResult) -> pd.DataFrame:
    response_time = payload.get("time") if isinstance(payload, dict) else None
    states = payload.get("states", []) if isinstance(payload, dict) else []
    rows = [_normalize_state_vector(state, response_time=response_time, status=status) for state in states if isinstance(state, list)]
    return pd.DataFrame(rows)


def fetch_opensky_state_vectors(
    *,
    time: int | None = None,
    icao24: str | list[str] | None = None,
    bounds: dict[str, float] | tuple[float, float, float, float] | None = None,
    extended: bool = False,
    allow_anonymous: bool = False,
    session: Any | None = None,
    ttl_seconds: int = 30,
    timeout: int = 10,
) -> tuple[pd.DataFrame, DataResult]:
    """Fetch authenticated OpenSky /states/all vectors and normalize them for War Room payloads."""
    params = build_opensky_states_params(time=time, icao24=icao24, bounds=bounds, extended=extended)
    headers = {"Accept": "application/json"}
    auth_mode = "anonymous"
    if opensky_credentials_configured():
        token, token_status = fetch_opensky_access_token(session=session, timeout=timeout)
        if not token:
            return pd.DataFrame(), token_status
        headers["Authorization"] = f"Bearer {token}"
        auth_mode = "oauth2"
    elif not allow_anonymous:
        return pd.DataFrame(), error_result(
            source="OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET",
            provider="opensky",
            error="Missing optional environment variable: OPENSKY_CLIENT_ID or OPENSKY_CLIENT_SECRET",
            warning="OpenSky /states/all probe not started; add OAuth2 client credentials or explicitly allow anonymous probing.",
            is_paid_required=True,
            coverage="missing key",
        )
    data, status = fetch_json_with_cache(
        _cache_key(params, auth_mode=auth_mode),
        OPENSKY_STATES_URL,
        provider="opensky",
        source="OpenSky /states/all",
        params=params,
        headers=headers,
        ttl_seconds=ttl_seconds,
        timeout=timeout,
        session=session,
    )
    if not status.ok:
        return pd.DataFrame(), status
    frame = normalize_opensky_states(data, status)
    if frame.empty:
        return frame, error_result(source=OPENSKY_STATES_URL, provider="opensky", error="No OpenSky state vectors returned.", data=frame, coverage="0 state vectors")
    status.data = frame
    status.coverage = f"{len(frame)} aircraft state vectors"
    if auth_mode == "anonymous":
        status.warning = "OpenSky anonymous probe was explicitly allowed; quotas and availability are limited."
    return frame, status
