from __future__ import annotations

import os
from typing import Any

import pandas as pd

from .env_loader import get_env_var
from .openbb_bridge import OPENBB_CAVEAT, get_openbb_version, is_openbb_installed


PROVIDER_SCHEMA = [
    "provider_id",
    "name",
    "domain",
    "description",
    "base_url",
    "requires_key",
    "env_var",
    "free_mode",
    "paid_optional",
    "supports_realtime",
    "supports_historical",
    "supports_streaming",
    "rate_limit_notes",
    "data_quality_notes",
    "license_notes",
    "is_configured",
    "is_available",
    "caveat",
]


def _provider(
    provider_id: str,
    name: str,
    domain: str,
    description: str,
    base_url: str,
    *,
    requires_key: bool = False,
    env_var: str | None = None,
    free_mode: bool = True,
    paid_optional: bool = False,
    supports_realtime: bool = False,
    supports_historical: bool = True,
    supports_streaming: bool = False,
    rate_limit_notes: str = "Provider-specific limits apply.",
    data_quality_notes: str = "Coverage and freshness vary by provider.",
    license_notes: str = "Review provider terms before production use.",
    caveat: str = "Optional provider; missing keys degrade gracefully.",
) -> dict[str, Any]:
    env_vars = [part.strip() for part in str(env_var or "").split(",") if part.strip()]
    configured = all(bool(get_env_var(name)) for name in env_vars) if env_vars else free_mode and not requires_key
    available = configured or (free_mode and not requires_key)
    return {
        "provider_id": provider_id,
        "name": name,
        "domain": domain,
        "description": description,
        "base_url": base_url,
        "requires_key": requires_key,
        "env_var": env_var or "",
        "free_mode": free_mode,
        "paid_optional": paid_optional,
        "supports_realtime": supports_realtime,
        "supports_historical": supports_historical,
        "supports_streaming": supports_streaming,
        "rate_limit_notes": rate_limit_notes,
        "data_quality_notes": data_quality_notes,
        "license_notes": license_notes,
        "is_configured": configured,
        "is_available": available,
        "caveat": caveat,
    }


def _openbb_provider() -> dict[str, Any]:
    installed = is_openbb_installed()
    version = get_openbb_version() if installed else None
    return {
        "provider_id": "openbb",
        "name": "OpenBB Optional Backend",
        "domain": "Market",
        "description": "Optional backend bridge for equity, ETF, macro, rates, options, and screener datasets.",
        "base_url": "local-python-package://openbb",
        "requires_key": False,
        "env_var": "",
        "free_mode": False,
        "paid_optional": True,
        "supports_realtime": False,
        "supports_historical": True,
        "supports_streaming": False,
        "rate_limit_notes": "Provider-specific limits apply through the configured OpenBB provider.",
        "data_quality_notes": "Coverage depends on installed OpenBB extensions, provider keys, and data rights.",
        "license_notes": f"{OPENBB_CAVEAT} Installed version: {version or 'not installed'}.",
        "is_configured": installed,
        "is_available": installed,
        "caveat": OPENBB_CAVEAT,
    }


def build_provider_registry() -> list[dict[str, Any]]:
    providers = [
        _provider("yfinance", "yfinance", "Market", "Equity, ETF, index, options, and crypto market data wrapper.", "https://query1.finance.yahoo.com", rate_limit_notes="Unofficial public endpoint; throttling can occur.", data_quality_notes="Delayed and adjusted fields vary by ticker."),
        _provider("fred", "FRED", "Market", "Macro and rates data through fredapi if configured.", "https://api.stlouisfed.org/fred", requires_key=True, env_var="FRED_API_KEY", free_mode=False, paid_optional=False, data_quality_notes="Free API key required by FRED."),
        _provider("eia", "EIA", "Market", "Energy inventory and production data.", "https://api.eia.gov", requires_key=True, env_var="EIA_API_KEY", free_mode=False, paid_optional=False),
        _provider("pykrx", "pykrx", "Market", "Korean market data wrapper when installed.", "https://github.com/sharebook-kr/pykrx", free_mode=True, rate_limit_notes="Library and upstream website limits apply."),
        _provider("alpha_vantage", "Alpha Vantage", "Market", "Optional equity, FX, and macro data.", "https://www.alphavantage.co", requires_key=True, env_var="ALPHAVANTAGE_API_KEY", free_mode=True, paid_optional=True, rate_limit_notes="Free tier is supported but rate-limited; cache and bounded refresh budgets are required."),
        _provider("finnhub", "Finnhub", "Market", "Optional equity, news, and fundamentals provider.", "https://finnhub.io", requires_key=True, env_var="FINNHUB_API_KEY", free_mode=False, paid_optional=True),
        _provider("polygon", "Polygon", "Market", "Optional high-quality market data provider.", "https://api.polygon.io", requires_key=True, env_var="POLYGON_API_KEY", free_mode=False, paid_optional=True),
        _provider("fmp", "Financial Modeling Prep", "Market", "Optional financial statements and market data.", "https://financialmodelingprep.com", requires_key=True, env_var="FMP_API_KEY", free_mode=False, paid_optional=True),
        _openbb_provider(),
        _provider("binance_futures", "Binance public futures", "Crypto", "Public futures derivatives endpoints.", "https://fapi.binance.com", supports_realtime=True, supports_streaming=True, rate_limit_notes="Public rate limits and IP restrictions apply."),
        _provider("coingecko", "CoinGecko", "Crypto", "Public crypto spot market data.", "https://api.coingecko.com/api/v3", rate_limit_notes="Public API throttles heavily."),
        _provider("defillama", "DefiLlama", "Crypto", "Public DeFi TVL and stablecoin data.", "https://api.llama.fi", rate_limit_notes="Public API limits apply."),
        _provider("coinglass", "CoinGlass", "Crypto", "Optional crypto derivatives and liquidation intelligence.", "https://open-api.coinglass.com", requires_key=True, env_var="COINGLASS_API_KEY", free_mode=False, paid_optional=True, supports_realtime=True, data_quality_notes="Liquidation maps require official provider access."),
        _provider("cryptoquant", "CryptoQuant", "Crypto", "Optional on-chain and derivatives data.", "https://api.cryptoquant.com", requires_key=True, env_var="CRYPTOQUANT_API_KEY", free_mode=False, paid_optional=True),
        _provider("glassnode", "Glassnode", "Crypto", "Optional on-chain analytics.", "https://api.glassnode.com", requires_key=True, env_var="GLASSNODE_API_KEY", free_mode=False, paid_optional=True),
        _provider("kaiko", "Kaiko", "Crypto", "Optional institutional crypto market data.", "https://us.market-api.kaiko.io", requires_key=True, env_var="KAIKO_API_KEY", free_mode=False, paid_optional=True),
        _provider("rss", "RSS feeds", "News / OSINT", "Curated public RSS feed polling.", "rss://public-feeds", supports_realtime=True, rate_limit_notes="Publisher limits apply.", data_quality_notes="Source quality varies; dedupe required."),
        _provider("gdelt", "GDELT", "News / OSINT", "Global event/news monitoring public endpoint.", "https://api.gdeltproject.org", supports_realtime=True, rate_limit_notes="Public API can throttle or return sparse windows."),
        _provider("yahoo_news", "Yahoo news", "News / OSINT", "Public Yahoo Finance news surfaces through wrappers.", "https://finance.yahoo.com", rate_limit_notes="Unofficial public endpoint; throttling can occur."),
        _provider("newsapi", "NewsAPI", "News / OSINT", "Optional news provider.", "https://newsapi.org", requires_key=True, env_var="NEWSAPI_KEY", free_mode=False, paid_optional=True),
        _provider("worldmonitor", "WorldMonitor adapter", "News / OSINT", "Optional adapter endpoint for configured WorldMonitor-compatible panels.", "WORLD_MONITOR_BASE_URL", requires_key=False, env_var="WORLD_MONITOR_BASE_URL", free_mode=False, paid_optional=True, supports_realtime=True, caveat="Reference-only adapter; no WorldMonitor source is imported."),
        _provider("acled", "ACLED", "Geopolitics / Conflict", "Optional conflict event provider.", "https://api.acleddata.com", requires_key=True, env_var="ACLED_API_KEY", free_mode=False, paid_optional=True),
        _provider("ucdp", "UCDP", "Geopolitics / Conflict", "Optional conflict dataset access.", "https://ucdp.uu.se", requires_key=False, env_var="UCDP_ENDPOINT", free_mode=False, paid_optional=True),
        _provider("curated_rss_conflict", "Curated conflict RSS", "Geopolitics / Conflict", "Public curated conflict and policy feeds.", "rss://curated-conflict", supports_realtime=True),
        _provider("usgs_earthquakes", "USGS earthquakes", "Natural / Weather", "Public earthquake feed.", "https://earthquake.usgs.gov", supports_realtime=True),
        _provider(
            "nasa_eonet",
            "NASA EONET",
            "Natural / Weather",
            "Open natural-event aggregation with source links and event geometry.",
            "https://eonet.gsfc.nasa.gov/api/v3",
            supports_realtime=True,
            rate_limit_notes="Public endpoint; use the project TTL cache and bounded normalized rows.",
            data_quality_notes="Events and geometries can revise; EONET aggregates upstream source observations.",
            license_notes="NASA-led data is generally open, but each upstream source and attribution requirement must be reviewed.",
            caveat="Informational event context only; preserve EONET and original-source provenance.",
        ),
        _provider("nasa_firms", "NASA FIRMS", "Natural / Weather", "Optional fire and thermal anomaly provider.", "https://firms.modaps.eosdis.nasa.gov", requires_key=True, env_var="NASA_FIRMS_MAP_KEY", free_mode=False, paid_optional=True, supports_realtime=True),
        _provider("weather_optional", "Weather providers", "Natural / Weather", "Optional weather data provider slot.", "WEATHER_API_BASE_URL", requires_key=True, env_var="WEATHER_API_KEY", free_mode=False, paid_optional=True, supports_realtime=True),
        _provider("aisstream", "AISStream", "AIS / Shipping", "Optional AIS streaming provider; live AIS unavailable unless configured and tested.", "wss://stream.aisstream.io", requires_key=True, env_var="AISSTREAM_API_KEY", free_mode=False, paid_optional=True, supports_realtime=True, supports_streaming=True, caveat="Live AIS unavailable unless configured and tested."),
        _provider("marinetraffic", "MarineTraffic", "AIS / Shipping", "Optional vessel data provider.", "https://services.marinetraffic.com", requires_key=True, env_var="MARINETRAFFIC_API_KEY", free_mode=False, paid_optional=True, supports_realtime=True),
        _provider("vesselfinder", "VesselFinder", "AIS / Shipping", "Optional vessel data provider.", "https://www.vesselfinder.com", requires_key=True, env_var="VESSELFINDER_API_KEY", free_mode=False, paid_optional=True),
        _provider("chokepoint_proxy", "Chokepoint proxy", "AIS / Shipping", "Static chokepoint and news-risk fallback.", "local://chokepoints", supports_realtime=False, supports_historical=False, data_quality_notes="Proxy only; no live vessel flow is claimed.", caveat="Live AIS unavailable. Displaying chokepoint/news risk proxy."),
        _provider("opensky", "OpenSky", "Flight", "Optional flight tracking provider.", "https://opensky-network.org/api", requires_key=True, env_var="OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET", free_mode=False, paid_optional=True, supports_realtime=True, caveat="Live flight tracking unavailable unless OAuth2 client credentials are configured and tested."),
        _provider("adsb_optional", "ADS-B providers", "Flight", "Optional ADS-B provider slot.", "ADSB_API_BASE_URL", requires_key=True, env_var="ADSB_API_KEY", free_mode=False, paid_optional=True, supports_realtime=True),
        _provider("polymarket", "Polymarket", "Prediction markets", "Optional prediction-market data.", "https://gamma-api.polymarket.com", free_mode=True, supports_realtime=True),
        _provider("kalshi", "Kalshi", "Prediction markets", "Optional prediction-market data.", "https://trading-api.kalshi.com", requires_key=True, env_var="KALSHI_API_KEY", free_mode=False, paid_optional=True),
    ]
    return [{key: provider.get(key) for key in PROVIDER_SCHEMA} for provider in providers]


def get_provider_definition(provider_id: str) -> dict[str, Any] | None:
    normalized = str(provider_id).lower()
    return next((provider for provider in build_provider_registry() if provider["provider_id"].lower() == normalized), None)


def list_providers_by_domain(domain: str) -> list[dict[str, Any]]:
    return [provider for provider in build_provider_registry() if provider["domain"].lower() == str(domain).lower()]


def list_available_providers() -> list[dict[str, Any]]:
    return [provider for provider in build_provider_registry() if provider["is_available"]]


def provider_requires_key(provider_id: str) -> bool:
    provider = get_provider_definition(provider_id)
    return bool(provider and provider["requires_key"])


def provider_env_status(provider_id: str) -> dict[str, Any]:
    provider = get_provider_definition(provider_id)
    if not provider:
        return {"provider_id": provider_id, "configured": False, "env_var": "", "status": "unknown provider"}
    env_var = provider["env_var"]
    env_vars = [part.strip() for part in str(env_var or "").split(",") if part.strip()]
    configured = all(bool(get_env_var(name)) for name in env_vars) if env_vars else provider["is_configured"]
    return {"provider_id": provider_id, "configured": configured, "env_var": env_var, "requires_key": provider["requires_key"], "status": "configured" if configured else "missing optional key" if provider["requires_key"] or env_var else "free mode"}


def provider_capability_matrix() -> pd.DataFrame:
    return pd.DataFrame(build_provider_registry(), columns=PROVIDER_SCHEMA)


def provider_priority_order(domain: str) -> list[str]:
    providers = list_providers_by_domain(domain)
    return [provider["provider_id"] for provider in sorted(providers, key=lambda item: (not item["is_available"], item["paid_optional"], item["provider_id"]))]
