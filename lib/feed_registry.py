from __future__ import annotations

from typing import Any


FEED_REGISTRY_SCHEMA = [
    "feed_id",
    "label",
    "provider",
    "category",
    "region",
    "source_url",
    "source_type",
    "tier",
    "default_enabled",
    "requires_key",
    "cadence_seconds",
    "credibility",
    "source_risk",
    "tags",
    "caveat",
]


def _feed(
    feed_id: str,
    label: str,
    provider: str,
    category: str,
    region: str,
    source_url: str,
    source_type: str,
    *,
    tier: str,
    default_enabled: bool,
    requires_key: bool = False,
    cadence_seconds: int = 3600,
    credibility: str = "secondary",
    source_risk: str = "medium",
    tags: list[str] | None = None,
    caveat: str = "",
) -> dict[str, Any]:
    return {
        "feed_id": feed_id,
        "label": label,
        "provider": provider,
        "category": category,
        "region": region,
        "source_url": source_url,
        "source_type": source_type,
        "tier": tier,
        "default_enabled": bool(default_enabled),
        "requires_key": bool(requires_key),
        "cadence_seconds": int(cadence_seconds),
        "credibility": credibility,
        "source_risk": source_risk,
        "tags": list(tags or []),
        "caveat": caveat,
    }


def build_feed_registry() -> list[dict[str, Any]]:
    """Return the curated, network-free public feed taxonomy."""
    feeds = [
        _feed(
            "rss.eia_today_energy",
            "EIA Today in Energy",
            "rss",
            "energy",
            "US / Global",
            "https://www.eia.gov/rss/todayinenergy.xml",
            "rss",
            tier="official",
            default_enabled=True,
            cadence_seconds=3600,
            credibility="official",
            source_risk="low",
            tags=["energy", "oil", "gas", "inventories", "official"],
            caveat="Official EIA RSS feed; publication cadence is not intraday market data.",
        ),
        _feed(
            "rss.fed_press_all",
            "Federal Reserve Press Releases",
            "rss",
            "macro",
            "US",
            "https://www.federalreserve.gov/feeds/press_all.xml",
            "rss",
            tier="official",
            default_enabled=True,
            cadence_seconds=3600,
            credibility="official",
            source_risk="low",
            tags=["macro", "rates", "policy", "official"],
            caveat="Official Federal Reserve RSS feed; rows are policy context, not trading signals.",
        ),
        _feed(
            "rss.iea_news",
            "IEA News",
            "rss",
            "energy",
            "Global",
            "https://www.iea.org/rss/news",
            "rss",
            tier="official",
            default_enabled=True,
            cadence_seconds=7200,
            credibility="official",
            source_risk="medium",
            tags=["energy", "oil", "gas", "transition", "official"],
            caveat="IEA feed availability can vary by public access controls.",
        ),
        _feed(
            "rss.opec_news",
            "OPEC News",
            "rss",
            "energy",
            "Global",
            "https://www.opec.org/opec_web/en/rss.xml",
            "rss",
            tier="official",
            default_enabled=True,
            cadence_seconds=7200,
            credibility="official",
            source_risk="medium",
            tags=["oil", "opec", "supply", "official"],
            caveat="OPEC RSS availability can be blocked or intermittent from some networks.",
        ),
        _feed(
            "gdelt.geopolitical_public",
            "GDELT Geopolitical Public Search",
            "gdelt",
            "news_osint",
            "Global",
            "https://api.gdeltproject.org/api/v2/doc/doc",
            "json_api",
            tier="public",
            default_enabled=True,
            cadence_seconds=900,
            credibility="secondary",
            source_risk="rate-limited/noisy",
            tags=["gdelt", "news", "geopolitics", "osint"],
            caveat="GDELT is public and noisy; verify original source URLs and timestamps.",
        ),
        _feed(
            "usgs.earthquakes_m25",
            "USGS Earthquakes M2.5+",
            "usgs_earthquake",
            "natural",
            "Global",
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            "geojson_api",
            tier="official",
            default_enabled=True,
            cadence_seconds=600,
            credibility="official",
            source_risk="low",
            tags=["earthquake", "natural", "hazard", "official"],
            caveat="USGS events can revise after initial publication.",
        ),
        _feed(
            "coingecko.public_markets",
            "CoinGecko Public Markets",
            "coingecko_public",
            "crypto",
            "Global",
            "https://api.coingecko.com/api/v3/coins/markets",
            "json_api",
            tier="public",
            default_enabled=True,
            cadence_seconds=120,
            credibility="secondary",
            source_risk="rate-limited",
            tags=["crypto", "spot", "market", "public"],
            caveat="Keyless CoinGecko requests are rate-limited and can be delayed.",
        ),
        _feed(
            "binance.futures_premium_index",
            "Binance Futures Premium Index",
            "binance_futures",
            "crypto",
            "Global",
            "https://fapi.binance.com/fapi/v1/premiumIndex",
            "json_api",
            tier="public",
            default_enabled=True,
            cadence_seconds=60,
            credibility="secondary",
            source_risk="exchange-specific/rate-limited",
            tags=["crypto", "futures", "funding", "exchange"],
            caveat="Exchange-specific public endpoint; regional access and terms must be verified.",
        ),
        _feed(
            "chokepoints.static_registry",
            "Energy Chokepoints Static Registry",
            "local",
            "shipping_energy",
            "Global",
            "local://static-chokepoints",
            "static_registry",
            tier="local",
            default_enabled=True,
            cadence_seconds=86400,
            credibility="context",
            source_risk="proxy/static",
            tags=["shipping", "energy", "chokepoint", "proxy"],
            caveat="Static context only; no live AIS or vessel-flow telemetry is claimed.",
        ),
        _feed(
            "sanctions.opensanctions_registry_only",
            "OpenSanctions Registry Slot",
            "opensanctions",
            "sanctions",
            "Global",
            "https://www.opensanctions.org/",
            "registry_only",
            tier="future_optional",
            default_enabled=False,
            cadence_seconds=86400,
            credibility="primary/compiled",
            source_risk="not-implemented",
            tags=["sanctions", "compliance", "registry"],
            caveat="Registry-only in this slice; no sanctions rows are fetched or displayed as live.",
        ),
        _feed(
            "ais.aisstream_optional",
            "AISStream Optional AIS Unavailable",
            "aisstream",
            "shipping_ais",
            "Global",
            "wss://stream.aisstream.io",
            "stream_optional",
            tier="optional",
            default_enabled=False,
            requires_key=True,
            cadence_seconds=30,
            credibility="provider",
            source_risk="missing-key",
            tags=["ais", "shipping", "vessels", "optional"],
            caveat="Unavailable unless a real AIS provider key is configured and successfully probed.",
        ),
        _feed(
            "flight.opensky_optional",
            "OpenSky Optional Flight Tracking",
            "opensky",
            "flight_tracking",
            "Global",
            "https://opensky-network.org",
            "api_optional",
            tier="optional",
            default_enabled=False,
            requires_key=True,
            cadence_seconds=60,
            credibility="provider",
            source_risk="missing-key",
            tags=["flight", "aviation", "adsb", "optional"],
            caveat="Unavailable unless a real flight provider is configured and successfully probed.",
        ),
    ]
    return [{key: feed.get(key) for key in FEED_REGISTRY_SCHEMA} for feed in feeds]


def get_feed_definition(feed_id: str) -> dict[str, Any] | None:
    normalized = str(feed_id or "").strip().lower()
    return next((feed for feed in build_feed_registry() if str(feed["feed_id"]).lower() == normalized), None)


def list_feeds_by_category(category: str) -> list[dict[str, Any]]:
    normalized = str(category or "").strip().lower()
    return [feed for feed in build_feed_registry() if str(feed["category"]).lower() == normalized]


def list_feeds_by_provider(provider: str) -> list[dict[str, Any]]:
    normalized = str(provider or "").strip().lower()
    return [feed for feed in build_feed_registry() if str(feed["provider"]).lower() == normalized]


def list_default_feeds(*, source_type: str | None = None, category: str | None = None) -> list[dict[str, Any]]:
    feeds = [feed for feed in build_feed_registry() if feed["default_enabled"] and not feed["requires_key"]]
    if source_type:
        normalized_type = str(source_type).strip().lower()
        feeds = [feed for feed in feeds if str(feed["source_type"]).lower() == normalized_type]
    if category:
        normalized_category = str(category).strip().lower()
        feeds = [feed for feed in feeds if str(feed["category"]).lower() == normalized_category]
    return feeds


def default_rss_feed_urls() -> list[str]:
    return [feed["source_url"] for feed in list_default_feeds(source_type="rss")]


def feed_definition_for_url(url: str) -> dict[str, Any] | None:
    normalized = str(url or "").strip().lower()
    return next((feed for feed in build_feed_registry() if str(feed["source_url"]).strip().lower() == normalized), None)


def feed_registry_table() -> list[dict[str, Any]]:
    return build_feed_registry()
