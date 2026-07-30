from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .data_status import DataResult, combine_results, error_result, ok_result
from .env_loader import get_env_var
from .feed_registry import default_rss_feed_urls, list_default_feeds
from .provider_registry import build_provider_registry
from .runtime_cache import fetch_json_with_cache


AIS_UNAVAILABLE_MESSAGE = "Live AIS unavailable. Displaying chokepoint/news risk proxy."
FLIGHT_UNAVAILABLE_MESSAGE = "Live flight tracking unavailable. Displaying optional provider status only."


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_from_ms(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return value.to_dict(orient="records")
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        if "data" in value:
            return _records(value.get("data"))
        if "items" in value:
            return _records(value.get("items"))
        return [dict(value)]
    return []


def _status_value(status: DataResult | None) -> str:
    return status.refreshed_status() if status is not None else "unknown"


def _source_status(status: DataResult | None) -> str:
    return _status_value(status)


def _public_headers() -> dict[str, str]:
    user_agent = (
        get_env_var("NEWS_FEED_USER_AGENT")
        or get_env_var("SEC_USER_AGENT")
        or get_env_var("NWS_USER_AGENT")
        or "GlobalMarketAnalystTerminal/1.0 source-backed runtime"
    )
    return {"User-Agent": user_agent, "Accept": "application/json, application/xml, text/xml;q=0.9, */*;q=0.8"}


def _attach_provenance(
    frame: pd.DataFrame,
    status: DataResult,
    *,
    provider: str,
    source_url: str | None = None,
    confidence: float = 0.6,
    coordinate_method: str = "unmapped",
    data_gap: str = "",
    caveat: str = "",
) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    enriched = frame.copy()
    fetched_at = status.fetched_at.isoformat() if getattr(status, "fetched_at", None) else _now_iso()
    source_status = _source_status(status)
    if "provider" not in enriched.columns:
        enriched["provider"] = provider
    else:
        enriched["provider"] = enriched["provider"].fillna(provider).replace("", provider)
    if "source_url" not in enriched.columns:
        enriched["source_url"] = source_url or status.source
    else:
        enriched["source_url"] = enriched["source_url"].fillna(source_url or status.source).replace("", source_url or status.source)
    if "fetched_at" not in enriched.columns:
        enriched["fetched_at"] = fetched_at
    else:
        enriched["fetched_at"] = enriched["fetched_at"].fillna(fetched_at).replace("", fetched_at)
    if "freshness" not in enriched.columns:
        enriched["freshness"] = source_status
    else:
        enriched["freshness"] = enriched["freshness"].fillna(source_status).replace("", source_status)
    if "source_status" not in enriched.columns:
        enriched["source_status"] = source_status
    else:
        enriched["source_status"] = enriched["source_status"].fillna(source_status).replace("", source_status)
    if "confidence" not in enriched.columns:
        enriched["confidence"] = confidence
    else:
        enriched["confidence"] = enriched["confidence"].fillna(confidence)
    if "coordinate_method" not in enriched.columns:
        enriched["coordinate_method"] = coordinate_method
    else:
        enriched["coordinate_method"] = enriched["coordinate_method"].fillna(coordinate_method).replace("", coordinate_method)
    if "data_gap" not in enriched.columns:
        enriched["data_gap"] = data_gap
    else:
        enriched["data_gap"] = enriched["data_gap"].fillna(data_gap)
    if "caveat" not in enriched.columns:
        enriched["caveat"] = caveat
    else:
        enriched["caveat"] = enriched["caveat"].fillna(caveat)
    return enriched


def _severity_from_magnitude(magnitude: Any) -> str:
    try:
        mag = float(magnitude)
    except Exception:
        return "watch"
    if mag >= 7:
        return "critical"
    if mag >= 6:
        return "high"
    if mag >= 5:
        return "elevated"
    return "watch"


def _crypto_stress_score(change_pct: Any) -> float:
    try:
        return min(100.0, abs(float(change_pct)) * 8.0)
    except Exception:
        return 0.0


def build_live_feed_config() -> dict[str, Any]:
    providers = build_provider_registry()
    return {
        "providers": providers,
        "polling_enabled_default": False,
        "streaming_enabled_default": False,
        "caveat": "Live and polling feeds are optional and should be started by explicit user action.",
    }


def fetch_rss_feed(urls: list[str] | None = None, *, parser=None) -> tuple[pd.DataFrame, object]:
    urls = list(urls or default_rss_feed_urls())
    rows = []
    if parser is not None:
        for url in urls:
            rows.extend(parser(url))
        frame = pd.DataFrame(rows)
        status = ok_result(frame, source="RSS", provider="rss", is_estimated=True, coverage=f"{len(frame)} RSS rows")
        return _attach_provenance(
            frame,
            status,
            provider="rss",
            source_url="rss://parser",
            confidence=0.55,
            coordinate_method="unmapped",
            caveat="Parser-supplied RSS rows; source terms vary by publisher.",
        ), status
    from .geopolitical_news import fetch_public_rss_news

    frame, status = fetch_public_rss_news(urls)
    if frame is None or frame.empty:
        return pd.DataFrame(), status
    enriched = _attach_provenance(
        frame,
        status,
        provider="rss",
        source_url="rss://public-feeds",
        confidence=0.62,
        coordinate_method="unmapped",
        caveat="Public RSS feeds can lag, duplicate, or revise stories.",
    )
    if "source_url" in enriched.columns and "url" in enriched.columns:
        enriched["source_url"] = enriched["url"].where(enriched["url"].astype(str).ne(""), enriched["source_url"])
    status.data = enriched
    status.coverage = f"{len(enriched)} RSS rows"
    return enriched, status


def fetch_gdelt_feed(query: str = "geopolitical risk", *, requester=None) -> tuple[pd.DataFrame, object]:
    if requester is not None:
        data = requester(query)
        frame = pd.DataFrame(data if isinstance(data, list) else data.get("articles", data.get("items", [])))
        status = ok_result(frame, source="GDELT", provider="gdelt", coverage=f"{len(frame)} rows")
        return _attach_provenance(
            frame,
            status,
            provider="gdelt",
            source_url="https://api.gdeltproject.org/api/v2/doc/doc",
            confidence=0.6,
            coordinate_method="unmapped",
            caveat="Requester-supplied GDELT rows; verify upstream timestamp and source URL.",
        ), status
    from .gdelt_provider import build_gdelt_doc_url

    url = build_gdelt_doc_url(query, max_records=25, params={"sort": "hybridrel"})
    data, status = fetch_json_with_cache(
        f"gdelt:doc:{query}:25",
        url,
        provider="gdelt",
        source="GDELT DOC",
        headers=_public_headers(),
        ttl_seconds=900,
        timeout=12,
    )
    if not status.ok:
        return pd.DataFrame(), status
    articles = data.get("articles", []) if isinstance(data, dict) else []
    rows = []
    for article in articles:
        if not isinstance(article, dict):
            continue
        rows.append(
            {
                "title": article.get("title") or "Untitled GDELT item",
                "summary": article.get("seendate") or article.get("language") or "",
                "url": article.get("url") or "",
                "source": article.get("domain") or article.get("sourceCountry") or "GDELT",
                "source_url": article.get("url") or url,
                "published_at": article.get("seendate") or article.get("date"),
                "credibility": "secondary",
                "provider": "gdelt",
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame, error_result(source="GDELT DOC", provider="gdelt", error="No GDELT articles returned.", data=frame)
    enriched = _attach_provenance(
        frame,
        status,
        provider="gdelt",
        source_url=url,
        confidence=0.6,
        coordinate_method="unmapped",
        caveat="GDELT is public and noisy; verify original source and publication time.",
    )
    status.data = enriched
    status.coverage = f"{len(enriched)} GDELT rows"
    return enriched, status


def fetch_live_news_feed(urls: list[str] | None = None, *, rss_parser=None, gdelt_requester=None, query: str = "geopolitical risk") -> tuple[pd.DataFrame, object]:
    rss, rss_status = fetch_rss_feed(urls, parser=rss_parser)
    gdelt, gdelt_status = fetch_gdelt_feed(query=query, requester=gdelt_requester)
    frame = pd.concat([rss, gdelt], ignore_index=True) if not rss.empty or not gdelt.empty else pd.DataFrame()
    if not frame.empty:
        status = combine_results([rss_status, gdelt_status], provider="live_feeds", source="RSS/GDELT")
        status.data = frame
        status.coverage = f"{len(frame)} rows"
        if not status.warning and any(not item.ok for item in [rss_status, gdelt_status]):
            status.warning = "Partial public feed availability; inspect source statuses."
    else:
        warning = "; ".join(item.error for item in [rss_status, gdelt_status] if getattr(item, "error", None)) or "All public news feeds returned empty."
        status = error_result(source="RSS/GDELT", provider="live_feeds", error="No live news rows available.", warning=warning, data=frame)
    return frame, status


def fetch_usgs_earthquakes(*, requester=None) -> tuple[pd.DataFrame, object]:
    from .usgs_earthquake_provider import build_usgs_earthquake_url

    params = {"minmagnitude": 2.5, "orderby": "time", "limit": 100}
    url = build_usgs_earthquake_url(params)
    if requester is not None:
        data = requester(url)
        status = ok_result(data, source=url, provider="usgs_earthquake", coverage="requester response")
    else:
        data, status = fetch_json_with_cache(
            "usgs:earthquakes:m2.5:latest",
            url,
            provider="usgs_earthquake",
            source="USGS Earthquake GeoJSON",
            headers=_public_headers(),
            ttl_seconds=600,
            timeout=10,
        )
    if not status.ok:
        return pd.DataFrame(), status
    features = data.get("features", []) if isinstance(data, dict) else []
    rows = []
    for feature in features:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [None, None, None])
        magnitude = props.get("mag")
        rows.append(
            {
                "title": props.get("title") or "USGS earthquake event",
                "summary": props.get("place") or "",
                "timestamp": _timestamp_from_ms(props.get("time")) or _now_iso(),
                "published_at": _timestamp_from_ms(props.get("time")),
                "magnitude": magnitude,
                "depth_km": coords[2] if len(coords) > 2 else None,
                "lon": coords[0] if len(coords) > 0 else None,
                "lat": coords[1] if len(coords) > 1 else None,
                "location": props.get("place"),
                "region": "Global",
                "domain": "natural",
                "severity": _severity_from_magnitude(magnitude),
                "source": "USGS Earthquake Hazards Program",
                "source_url": props.get("url") or url,
                "url": props.get("url") or url,
                "provider": "usgs_earthquake",
                "credibility": "official",
                "confidence": 0.95,
                "coordinate_method": "usgs_geojson",
                "data_gap": "" if magnitude is not None and len(coords) >= 2 else "USGS event missing magnitude or coordinates.",
                "caveat": "USGS events can revise after initial publication.",
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame, error_result(source=url, provider="usgs_earthquake", error="No USGS earthquake features returned.", data=frame)
    enriched = _attach_provenance(
        frame,
        status,
        provider="usgs_earthquake",
        source_url=url,
        confidence=0.95,
        coordinate_method="usgs_geojson",
        caveat="USGS events can revise after initial publication.",
    )
    status.data = enriched
    status.coverage = f"{len(enriched)} earthquake events"
    return enriched, status


def fetch_nasa_eonet_events(
    *,
    requester=None,
    days: int = 30,
    limit: int = 200,
) -> tuple[pd.DataFrame, object]:
    from .eonet_provider import build_eonet_events_url, normalize_eonet_geojson

    url = build_eonet_events_url(days=days, status="open")
    if requester is not None:
        data = requester(url)
        status = ok_result(data, source=url, provider="nasa_eonet", coverage="requester response")
    else:
        data, status = fetch_json_with_cache(
            f"nasa:eonet:open:{min(max(int(days), 1), 365)}",
            url,
            provider="nasa_eonet",
            source="NASA EONET v3 GeoJSON",
            headers=_public_headers(),
            ttl_seconds=600,
            timeout=15,
        )
    if not status.ok:
        return pd.DataFrame(), status
    fetched_at = status.fetched_at.isoformat() if getattr(status, "fetched_at", None) else _now_iso()
    rows = normalize_eonet_geojson(data, fetched_at=fetched_at, limit=limit)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame, error_result(
            source=url,
            provider="nasa_eonet",
            error="No coordinate-backed NASA EONET events returned.",
            data=frame,
        )
    enriched = _attach_provenance(
        frame,
        status,
        provider="nasa_eonet",
        source_url=url,
        confidence=0.9,
        coordinate_method="nasa_eonet_geojson_point",
        caveat=(
            "NASA EONET aggregates natural-event metadata from upstream sources; "
            "verify revisions and original-source terms."
        ),
    )
    status.data = enriched
    status.coverage = f"{len(enriched)} deduplicated NASA EONET events"
    return enriched, status


def fetch_eia_latest_if_key(*, requester=None) -> tuple[Any, object]:
    if not get_env_var("EIA_API_KEY"):
        return None, error_result(source="EIA_API_KEY", provider="eia", error="Missing optional environment variable: EIA_API_KEY", warning="EIA latest data unavailable without key.", is_paid_required=True)
    if requester is None:
        return None, ok_result({}, source="EIA", provider="eia", warning="EIA key configured; no live requester supplied.", coverage="configured")
    data = requester(get_env_var("EIA_API_KEY"))
    return data, ok_result(data, source="EIA", provider="eia", coverage="latest response")


def fetch_binance_force_orders_optional(symbol: str = "BTCUSDT", *, requester=None) -> tuple[pd.DataFrame, object]:
    url = "https://fapi.binance.com/fapi/v1/forceOrders"
    if requester is None:
        return pd.DataFrame(), error_result(source=url, provider="binance_futures", error="Binance force-order stream is not fetched keylessly in this runtime slice.", warning="Use configured/verified derivatives providers before displaying liquidation feeds.")
    data = requester(url, {"symbol": symbol})
    frame = pd.DataFrame(data if isinstance(data, list) else [])
    status = ok_result(frame, source=url, provider="binance_futures", coverage=f"{len(frame)} rows", is_estimated=True)
    return _attach_provenance(frame, status, provider="binance_futures", source_url=url, confidence=0.5, coordinate_method="not_applicable", caveat="Force-order rows are derivatives context, not official liquidation heatmaps."), status


def fetch_binance_funding_live(symbol: str = "BTCUSDT", *, requester=None) -> tuple[Any, object]:
    url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    params = {"symbol": symbol}
    if requester is not None:
        data = requester(url, params)
        return data, ok_result(data, source=url, provider="binance_futures", coverage="premium index")
    data, status = fetch_json_with_cache(
        f"binance:futures:premiumIndex:{symbol}",
        url,
        provider="binance_futures",
        source="Binance futures premium index",
        params=params,
        ttl_seconds=60,
        timeout=8,
    )
    return data, status


def fetch_crypto_market_live(symbols: list[str] | None = None, *, requester=None) -> tuple[pd.DataFrame, object]:
    symbols = symbols or ["bitcoin", "ethereum"]
    if requester is None:
        from .coingecko_public_provider import build_coingecko_public_url

        params = {
            "vs_currency": "usd",
            "ids": ",".join(symbols),
            "order": "market_cap_desc",
            "per_page": min(max(len(symbols), 1), 250),
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h",
        }
        url = build_coingecko_public_url(params=params)
        data, status = fetch_json_with_cache(
            f"coingecko:markets:{','.join(symbols)}",
            url,
            provider="coingecko_public",
            source="CoinGecko public markets",
            ttl_seconds=120,
            timeout=10,
        )
        if not status.ok:
            return pd.DataFrame(), status
    else:
        data = requester(symbols)
        status = ok_result(data, source="CoinGecko", provider="coingecko_public", coverage="requester response")
        url = "https://api.coingecko.com/api/v3/coins/markets"
    rows = []
    source_rows = data if isinstance(data, list) else data.get("items", data.get("data", [])) if isinstance(data, dict) else []
    for item in source_rows:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or item.get("id") or "crypto").upper()
        change_pct = item.get("price_change_percentage_24h") or item.get("price_change_percentage_24h_in_currency")
        rows.append(
            {
                "symbol": symbol,
                "ticker": symbol,
                "title": f"{symbol} public crypto market state",
                "summary": f"CoinGecko spot price {item.get('current_price')}; 24h change {change_pct}.",
                "price": item.get("current_price"),
                "market_cap": item.get("market_cap"),
                "volume": item.get("total_volume"),
                "change_pct_24h": change_pct,
                "stress_score": _crypto_stress_score(change_pct),
                "domain": "crypto",
                "region": "Global",
                "source": "CoinGecko public markets",
                "source_url": url,
                "url": url,
                "provider": "coingecko_public",
                "credibility": "secondary",
                "confidence": 0.72,
                "coordinate_method": "not_applicable",
                "data_gap": "" if item.get("current_price") is not None else "CoinGecko row missing current_price.",
                "caveat": "CoinGecko keyless requests are rate-limited and may be delayed.",
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame, error_result(source="CoinGecko public markets", provider="coingecko_public", error="No CoinGecko market rows returned.", data=frame)
    enriched = _attach_provenance(
        frame,
        status,
        provider="coingecko_public",
        source_url=url,
        confidence=0.72,
        coordinate_method="not_applicable",
        caveat="CoinGecko keyless requests are rate-limited and may be delayed.",
    )
    status.data = enriched
    status.coverage = f"{len(enriched)} crypto assets"
    return enriched, status


def _binance_funding_event(symbol: str = "BTCUSDT") -> tuple[list[dict[str, Any]], DataResult]:
    data, status = fetch_binance_funding_live(symbol)
    if not status.ok or not isinstance(data, dict):
        return [], status
    source_url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    try:
        funding_rate = float(data.get("lastFundingRate") or 0.0)
    except Exception:
        funding_rate = 0.0
    row = {
        "symbol": data.get("symbol") or symbol,
        "ticker": data.get("symbol") or symbol,
        "title": f"{data.get('symbol') or symbol} Binance futures funding state",
        "summary": f"Last funding rate {funding_rate:.6f}; mark price {data.get('markPrice')}.",
        "funding_rate": funding_rate,
        "price": data.get("markPrice"),
        "stress_score": min(100.0, abs(funding_rate) * 100000.0),
        "domain": "crypto",
        "region": "Global",
        "source": "Binance futures premium index",
        "source_url": source_url,
        "url": source_url,
        "provider": "binance_futures",
        "credibility": "secondary",
        "confidence": 0.7,
        "coordinate_method": "not_applicable",
        "fetched_at": status.fetched_at.isoformat(),
        "freshness": status.refreshed_status(),
        "source_status": status.refreshed_status(),
        "data_gap": "Binance public funding is exchange-specific and not a whole-market view.",
        "caveat": "Exchange terms, availability, and regional access must be verified.",
    }
    status.data = [row]
    status.coverage = "1 Binance funding row"
    return [row], status


def build_keyless_runtime_feeds(
    *,
    query: str = "geopolitical risk OR oil OR earthquake OR crypto",
    include_news: bool = True,
    include_earthquakes: bool = True,
    include_nasa_eonet: bool = True,
    include_crypto: bool = True,
    include_flights: bool = False,
) -> dict[str, Any]:
    news = pd.DataFrame()
    natural_frames: list[pd.DataFrame] = []
    crypto = pd.DataFrame()
    flight = pd.DataFrame()
    statuses: list[DataResult] = []
    if include_news:
        news, news_status = fetch_live_news_feed(query=query)
        statuses.append(news_status)
    if include_earthquakes:
        earthquakes, natural_status = fetch_usgs_earthquakes()
        statuses.append(natural_status)
        if not earthquakes.empty:
            natural_frames.append(earthquakes)
    if include_nasa_eonet:
        eonet, eonet_status = fetch_nasa_eonet_events()
        statuses.append(eonet_status)
        if not eonet.empty:
            natural_frames.append(eonet)
    natural = pd.concat(natural_frames, ignore_index=True) if natural_frames else pd.DataFrame()
    if include_crypto:
        crypto, crypto_status = fetch_crypto_market_live()
        statuses.append(crypto_status)
        funding_rows, funding_status = _binance_funding_event()
        statuses.append(funding_status)
        if funding_rows:
            crypto = pd.concat([crypto, pd.DataFrame(funding_rows)], ignore_index=True) if not crypto.empty else pd.DataFrame(funding_rows)
    if include_flights:
        from .opensky_provider import fetch_opensky_state_vectors

        flight, flight_status = fetch_opensky_state_vectors()
        statuses.append(flight_status)
    data_gaps = [
        f"{status.provider}: {status.error or status.warning}"
        for status in statuses
        if not status.ok or status.warning
    ]
    return {
        "news": news.to_dict(orient="records") if hasattr(news, "to_dict") else [],
        "natural": natural.to_dict(orient="records") if hasattr(natural, "to_dict") else [],
        "crypto": crypto.to_dict(orient="records") if hasattr(crypto, "to_dict") else [],
        "flight": flight.to_dict(orient="records") if hasattr(flight, "to_dict") else [],
        "source_statuses": statuses,
        "source_status": [status.to_dict() for status in statuses],
        "feed_registry": list_default_feeds(),
        "data_gaps": data_gaps,
        "fetched_at": _now_iso(),
        "caveat": "Keyless runtime feeds use public endpoints with cache/stale fallback and explicit provider failures.",
    }


def fetch_aisstream_optional_status() -> dict[str, Any]:
    configured = bool(get_env_var("AISSTREAM_API_KEY"))
    return {
        "provider": "aisstream",
        "configured": configured,
        "available": configured,
        "status": "configured" if configured else "unavailable",
        "warning": None if configured else AIS_UNAVAILABLE_MESSAGE,
        "caveat": "Live AIS unavailable unless an optional AIS provider key is configured and tested.",
    }


def fetch_opensky_optional_status() -> dict[str, Any]:
    from .opensky_provider import build_opensky_optional_status

    status = build_opensky_optional_status()
    if status.get("warning"):
        status["warning"] = FLIGHT_UNAVAILABLE_MESSAGE
    return status


def fetch_opensky_state_vectors(*args, **kwargs):
    from .opensky_provider import fetch_opensky_state_vectors as _fetch_opensky_state_vectors

    return _fetch_opensky_state_vectors(*args, **kwargs)


def fetch_worldmonitor_optional_panels(*, adapter=None) -> tuple[Any, object]:
    if not get_env_var("WORLD_MONITOR_BASE_URL"):
        return None, error_result(source="WORLD_MONITOR_BASE_URL", provider="worldmonitor", error="WORLD_MONITOR_BASE_URL is not configured.", warning="WorldMonitor adapter is optional and reference-boundary safe.")
    if adapter is None:
        from .worldmonitor_adapter import get_public_panel_metadata

        result = get_public_panel_metadata()
        return result.data, result
    data = adapter()
    return data, ok_result(data, source="WorldMonitor adapter", provider="worldmonitor", coverage="adapter response")


def build_live_feed_status() -> pd.DataFrame:
    rows = []
    for provider in build_provider_registry():
        if provider["domain"] in {"AIS / Shipping", "Flight", "News / OSINT", "Natural / Weather", "Crypto"}:
            rows.append(
                {
                    "provider": provider["provider_id"],
                    "domain": provider["domain"],
                    "configured": provider["is_configured"],
                    "available": provider["is_available"],
                    "supports_realtime": provider["supports_realtime"],
                    "supports_streaming": provider["supports_streaming"],
                    "caveat": provider["caveat"],
                }
            )
    return pd.DataFrame(rows)
