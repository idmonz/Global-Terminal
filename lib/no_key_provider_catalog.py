from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


NO_KEY_PROVIDERS: list[dict[str, Any]] = [
    {"provider_id": "sec_edgar", "name": "SEC EDGAR", "purpose": "Company filings and facts", "env_var": "SEC_USER_AGENT", "access_model": "free_user_agent", "key_required": True, "no_key_fallback": False, "source_type": "official", "pages": ["Financial Terminal"], "caveat": "A descriptive User-Agent is required by SEC access policy."},
    {"provider_id": "treasury_fiscal", "name": "Treasury Fiscal Data", "purpose": "US fiscal and Treasury datasets", "env_var": "", "access_model": "no_key", "key_required": False, "no_key_fallback": True, "source_type": "official", "pages": ["Macro", "Data Provider Center"], "caveat": "Schemas and update schedules vary by dataset."},
    {"provider_id": "worldbank", "name": "World Bank", "purpose": "Country macro indicators", "env_var": "", "access_model": "no_key", "key_required": False, "no_key_fallback": True, "source_type": "official", "pages": ["Macro"], "caveat": "Country indicator updates may lag."},
    {"provider_id": "sdmx", "name": "SDMX Public APIs", "purpose": "Official statistical datasets", "env_var": "", "access_model": "no_key", "key_required": False, "no_key_fallback": True, "source_type": "official", "pages": ["Macro"], "caveat": "Endpoint contracts differ across SDMX providers."},
    {"provider_id": "gdelt", "name": "GDELT", "purpose": "Global news/event search", "env_var": "", "access_model": "no_key", "key_required": False, "no_key_fallback": True, "source_type": "public", "pages": ["News", "War Room"], "caveat": "News matching is noisy and source freshness must be checked."},
    {"provider_id": "usgs_earthquake", "name": "USGS Earthquake", "purpose": "Earthquake events", "env_var": "", "access_model": "no_key", "key_required": False, "no_key_fallback": True, "source_type": "official", "pages": ["War Room"], "caveat": "Event feeds can revise after initial publication."},
    {"provider_id": "open_meteo", "name": "Open-Meteo", "purpose": "Weather forecast context", "env_var": "", "access_model": "no_key", "key_required": False, "no_key_fallback": True, "source_type": "public", "pages": ["Energy / Geopolitics"], "caveat": "Forecasts are delayed/model-based and source terms should be verified."},
    {"provider_id": "nws", "name": "National Weather Service", "purpose": "US official weather alerts/points", "env_var": "NWS_USER_AGENT", "access_model": "free_user_agent", "key_required": True, "no_key_fallback": False, "source_type": "official", "pages": ["Energy / Geopolitics"], "caveat": "A descriptive User-Agent is required."},
    {"provider_id": "noaa_accessais", "name": "NOAA AccessAIS", "purpose": "Historical AIS archives", "env_var": "", "access_model": "no_key", "key_required": False, "no_key_fallback": True, "source_type": "official_historical_only", "pages": ["War Room", "Energy / Geopolitics"], "caveat": "Historical-only source; no live AIS is claimed."},
    {"provider_id": "binance_public", "name": "Binance Public", "purpose": "Public crypto market data", "env_var": "", "access_model": "no_key", "key_required": False, "no_key_fallback": True, "source_type": "public", "pages": ["Crypto Intelligence"], "caveat": "Exchange terms, availability, and region access must be verified."},
    {"provider_id": "defillama", "name": "DefiLlama", "purpose": "DeFi protocol and stablecoin data", "env_var": "", "access_model": "no_key", "key_required": False, "no_key_fallback": True, "source_type": "public", "pages": ["Crypto Intelligence"], "caveat": "Community/public dataset; verify methodology before relying on outputs."},
    {"provider_id": "coingecko_public", "name": "CoinGecko Public", "purpose": "Crypto prices and metadata", "env_var": "COINGECKO_API_KEY", "access_model": "no_key_with_optional_key", "key_required": False, "no_key_fallback": True, "source_type": "public", "pages": ["Crypto Intelligence"], "caveat": "Keyless requests are rate-limited."},
    {"provider_id": "fred", "name": "FRED", "purpose": "US macro series", "env_var": "FRED_API_KEY", "access_model": "free_key", "key_required": False, "no_key_fallback": True, "source_type": "official", "pages": ["Macro"], "caveat": "Key improves official API access; native fallback may be limited."},
    {"provider_id": "eia", "name": "EIA", "purpose": "Energy statistics", "env_var": "EIA_API_KEY", "access_model": "free_key", "key_required": False, "no_key_fallback": True, "source_type": "official", "pages": ["Energy / Geopolitics"], "caveat": "Some EIA endpoints require a free key."},
    {"provider_id": "nasa_firms", "name": "NASA FIRMS", "purpose": "Fire/hotspot context", "env_var": "NASA_FIRMS_MAP_KEY", "access_model": "free_key", "key_required": True, "no_key_fallback": False, "source_type": "official", "pages": ["War Room"], "caveat": "Never shown as connected without MAP_KEY."},
    {"provider_id": "aisstream", "name": "AISStream", "purpose": "AIS stream", "env_var": "AISSTREAM_API_KEY", "access_model": "free_key_optional_stream", "key_required": True, "no_key_fallback": False, "source_type": "optional_live", "pages": ["War Room"], "caveat": "Never shown as live without API key and a successful probe."},
    {"provider_id": "opensky", "name": "OpenSky", "purpose": "Flight tracking", "env_var": "OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET", "access_model": "oauth_optional", "key_required": False, "no_key_fallback": True, "source_type": "official/public", "pages": ["War Room"], "caveat": "OAuth credentials are supported but not required for base launch."},
]


def list_no_key_providers() -> list[dict[str, Any]]:
    return [dict(item) for item in NO_KEY_PROVIDERS]


def get_no_key_provider(provider_id: str) -> dict[str, Any] | None:
    needle = str(provider_id or "").lower()
    return next((item for item in list_no_key_providers() if item["provider_id"] == needle), None)


def build_no_key_provider_table():
    load_project_env()
    rows = []
    for item in list_no_key_providers():
        env_vars = [part.strip() for part in str(item.get("env_var", "")).split(",") if part.strip()]
        configured = all(get_env_var(env) for env in env_vars) if env_vars else True
        status = "historical_only" if item["provider_id"] == "noaa_accessais" else "configured" if configured else "missing_key" if item["key_required"] else "no_key_fallback"
        rows.append({**item, "configured": configured, "status": status})
    return pd.DataFrame(rows) if pd is not None else rows


def classify_provider_access(provider_id: str) -> str:
    provider = get_no_key_provider(provider_id) or {}
    return str(provider.get("access_model", "unknown"))
from .env_loader import get_env_var, load_project_env
