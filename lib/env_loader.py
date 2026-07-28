from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    from dotenv import dotenv_values, load_dotenv
except Exception:  # pragma: no cover
    dotenv_values = None
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT_DIR / ".env"

ENV_ALIASES: dict[str, list[str]] = {
    "ALPHAVANTAGE_API_KEY": ["ALPHA_VANTAGE_API_KEY"],
    "ALPHA_VANTAGE_API_KEY": ["ALPHAVANTAGE_API_KEY"],
    "OPENSKY_USERNAME": ["OPENSKY_CLIENT_ID"],
    "OPENSKY_PASSWORD": ["OPENSKY_CLIENT_SECRET"],
    "OPENSKY_CLIENT_ID": ["OPENSKY_USERNAME"],
    "OPENSKY_CLIENT_SECRET": ["OPENSKY_PASSWORD"],
}

PROVIDER_ENV_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "fred": {"required": [], "optional": ["FRED_API_KEY"]},
    "eia": {"required": [], "optional": ["EIA_API_KEY"]},
    "bls": {"required": [], "optional": ["BLS_API_KEY"]},
    "sec_edgar": {"required": ["SEC_USER_AGENT"], "optional": []},
    "nws": {"required": ["NWS_USER_AGENT"], "optional": []},
    "nasa_firms": {"required": [], "optional": ["NASA_FIRMS_MAP_KEY"]},
    "aisstream": {"required": [], "optional": ["AISSTREAM_API_KEY"]},
    "opensky": {"required": [], "optional": ["OPENSKY_CLIENT_ID", "OPENSKY_CLIENT_SECRET"]},
    "coingecko": {"required": [], "optional": ["COINGECKO_API_KEY"]},
    "alphavantage": {"required": [], "optional": ["ALPHAVANTAGE_API_KEY"]},
    "finnhub": {"required": [], "optional": ["FINNHUB_API_KEY"]},
    "bok_ecos": {"required": [], "optional": ["BOK_ECOS_API_KEY"]},
    "opendart": {"required": [], "optional": ["OPENDART_API_KEY"]},
    "kosis": {"required": [], "optional": ["KOSIS_API_KEY"]},
    "krx": {"required": [], "optional": ["KRX_API_KEY"]},
}


def load_project_env(env_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(env_path) if env_path is not None else DEFAULT_ENV_PATH
    if load_dotenv is None:
        return {"loaded": False, "path": str(path), "exists": path.exists(), "warning": "python-dotenv is unavailable"}
    loaded = load_dotenv(path, override=False) if path.exists() else False
    patched_blank_values: list[str] = []
    if path.exists() and dotenv_values is not None:
        values = dotenv_values(path)
        for key, value in values.items():
            if value and os.environ.get(key, "") == "":
                os.environ[key] = value
                patched_blank_values.append(key)
    return {
        "loaded": bool(loaded),
        "path": str(path),
        "exists": path.exists(),
        "warning": None,
        "patched_blank_values": patched_blank_values,
    }


def get_env_var(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value in (None, ""):
        for alias in ENV_ALIASES.get(name, []):
            value = os.getenv(alias)
            if value not in (None, ""):
                break
    if value is None or value == "":
        return default
    return value


def _mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 5:
        return "*" * len(value)
    return f"{value[:3]}...{value[-2:]}"


def get_masked_env_status(name: str) -> dict[str, Any]:
    value = get_env_var(name)
    configured = value is not None
    return {
        "env_var": name,
        "configured": configured,
        "status": "configured" if configured else "missing_key",
        "masked_value": _mask_secret(value),
    }


def required_env_vars_for_provider(provider: str) -> list[str]:
    return list(PROVIDER_ENV_REQUIREMENTS.get(provider.lower(), {}).get("required", []))


def optional_env_vars_for_provider(provider: str) -> list[str]:
    return list(PROVIDER_ENV_REQUIREMENTS.get(provider.lower(), {}).get("optional", []))


def build_env_status_table(providers: list[str] | None = None):
    provider_ids = providers or sorted(PROVIDER_ENV_REQUIREMENTS)
    rows: list[dict[str, Any]] = []
    for provider in provider_ids:
        requirements = PROVIDER_ENV_REQUIREMENTS.get(provider.lower(), {"required": [], "optional": []})
        for requirement_type, names in requirements.items():
            for name in names:
                status = get_masked_env_status(name)
                rows.append(
                    {
                        "provider": provider,
                        "env_var": name,
                        "requirement": requirement_type,
                        "configured": status["configured"],
                        "status": status["status"],
                        "masked_value": status["masked_value"],
                    }
                )
        if not requirements.get("required") and not requirements.get("optional"):
            rows.append(
                {
                    "provider": provider,
                    "env_var": "",
                    "requirement": "none",
                    "configured": True,
                    "status": "no_key_required",
                    "masked_value": "",
                }
            )
    return pd.DataFrame(rows) if pd is not None else rows
