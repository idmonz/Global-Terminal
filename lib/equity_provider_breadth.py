from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .env_loader import get_env_var
from .runtime_cache import RuntimeCacheRecord, load_runtime_cache_record, save_runtime_cache_record

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
EQUITY_BREADTH_TTL_SECONDS = 21_600
EQUITY_NEWS_TTL_SECONDS = 900
EQUITY_STALE_SECONDS = 172_800
EQUITY_EARNINGS_TTL_SECONDS = 21_600


def build_equity_provider_breadth(identity: dict[str, Any], *, session: Any | None = None) -> dict[str, Any]:
    """Return free-first equity provider context without leaking local keys."""
    if str(identity.get("asset_class") or "").lower() != "equity":
        return _not_applicable("Equity provider breadth is only attached to single-name equities.")
    symbol = _symbol(identity)
    alpha = fetch_alpha_vantage_overview(symbol, session=session)
    finnhub = fetch_finnhub_profile(symbol, session=session)
    providers = [alpha, finnhub]
    metrics = {**_record(alpha.get("metrics")), **_record(finnhub.get("metrics"))}
    profile = {**_record(alpha.get("profile")), **_record(finnhub.get("profile"))}
    source_register = [_source_row(row) for row in providers]
    available = [row for row in providers if row.get("availability") == "available"]
    gaps = [row.get("data_gap") for row in providers if row.get("data_gap")]
    return {
        "availability": "available" if available else "provider-required" if any(row.get("source_status") == "missing-key" for row in providers) else "unavailable",
        "provider": "Alpha Vantage + Finnhub",
        "source_status": _combined_status(providers),
        "source_url": "https://www.alphavantage.co/documentation/ ; https://finnhub.io/docs/api",
        "fetched_at": _latest_fetched_at(providers),
        "metrics": metrics,
        "profile": profile,
        "provider_rows": providers,
        "source_register": source_register,
        "caveat": "Free-tier equity context is supplemental. It is not licensed reference data, advice, target-price guidance, broker routing or execution.",
        "data_gap": "; ".join(str(item) for item in gaps if item) or None,
        "not_financial_advice": True,
    }


def build_equity_news_context(identity: dict[str, Any], *, session: Any | None = None, limit: int = 8) -> dict[str, Any]:
    if str(identity.get("asset_class") or "").lower() != "equity":
        return _not_applicable("Equity news providers are not attached to this asset class.")
    symbol = _symbol(identity)
    alpha = fetch_alpha_vantage_news(symbol, session=session, limit=limit)
    finnhub = fetch_finnhub_company_news(symbol, session=session, limit=limit)
    providers = [alpha, finnhub]
    rows = _dedupe_news([*_rows(alpha.get("rows")), *_rows(finnhub.get("rows"))], limit=limit)
    gaps = [row.get("data_gap") for row in providers if row.get("data_gap")]
    return {
        "availability": "available" if rows else "provider-required" if any(row.get("source_status") == "missing-key" for row in providers) else "unavailable",
        "provider": "Alpha Vantage + Finnhub",
        "source_status": _combined_status(providers),
        "source_url": "https://www.alphavantage.co/documentation/ ; https://finnhub.io/docs/api",
        "fetched_at": _latest_fetched_at(providers),
        "rows": rows,
        "source_register": [_source_row(row) for row in providers],
        "match_terms": [symbol],
        "caveat": "Company-news rows are source-bounded public/free-tier provider rows and must be verified at the linked publisher.",
        "data_gap": "; ".join(str(item) for item in gaps if item) or None,
        "not_financial_advice": True,
    }


def build_equity_earnings_context(
    identity: dict[str, Any],
    *,
    session: Any | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    if str(identity.get("asset_class") or "").lower() != "equity":
        return _not_applicable("Earnings and company calendar rows apply only to single-name equities.")
    symbol = _symbol(identity)
    alpha = fetch_alpha_vantage_earnings(symbol, session=session, limit=limit)
    finnhub = fetch_finnhub_earnings_calendar(symbol, session=session, limit=limit)
    providers = [alpha, finnhub]
    rows = _dedupe_earnings([*_rows(alpha.get("rows")), *_rows(finnhub.get("rows"))], limit=limit)
    gaps = [row.get("data_gap") for row in providers if row.get("data_gap")]
    missing_key_only = all(row.get("source_status") == "missing-key" for row in providers)
    return {
        "availability": "available" if rows else "provider-required" if missing_key_only else "unavailable",
        "provider": "Alpha Vantage + Finnhub",
        "source_status": _combined_status(providers),
        "source_url": "https://www.alphavantage.co/documentation/ ; https://finnhub.io/docs/api",
        "fetched_at": _latest_fetched_at(providers),
        "rows": rows,
        "reported_count": sum(row.get("event_type") == "reported-earnings" for row in rows),
        "scheduled_count": sum(row.get("event_type") == "scheduled-earnings" for row in rows),
        "provider_rows": providers,
        "source_register": [_source_row(row) for row in providers],
        "caveat": "Reported results and scheduled calendar rows remain separate. Provider dates can be revised and do not imply trading guidance.",
        "data_gap": "; ".join(str(item) for item in gaps if item) or None,
        "not_financial_advice": True,
    }


def fetch_alpha_vantage_overview(symbol: str, *, api_key: str | None = None, session: Any | None = None) -> dict[str, Any]:
    key = api_key or get_env_var("ALPHAVANTAGE_API_KEY") or get_env_var("ALPHA_VANTAGE_API_KEY")
    if not key:
        return _missing_key("Alpha Vantage", "ALPHAVANTAGE_API_KEY", ALPHA_VANTAGE_BASE_URL, source="alpha-vantage-overview")
    payload, meta = _fetch_json_cached(
        f"phase5x:alpha-vantage:overview:{symbol.upper()}",
        ALPHA_VANTAGE_BASE_URL,
        provider="Alpha Vantage",
        source="alpha-vantage-overview",
        params={"function": "OVERVIEW", "symbol": symbol.upper(), "apikey": key},
        ttl_seconds=EQUITY_BREADTH_TTL_SECONDS,
        session=session,
    )
    if payload is None:
        return _provider_gap("Alpha Vantage", ALPHA_VANTAGE_BASE_URL, source="alpha-vantage-overview", **meta)
    metrics = {
        "alpha_market_cap": _number(payload.get("MarketCapitalization")),
        "alpha_pe_ratio": _number(payload.get("PERatio")),
        "alpha_peg_ratio": _number(payload.get("PEGRatio")),
        "alpha_eps": _number(payload.get("EPS")),
        "alpha_revenue_ttm": _number(payload.get("RevenueTTM")),
        "alpha_profit_margin": _ratio(payload.get("ProfitMargin")),
        "alpha_operating_margin": _ratio(payload.get("OperatingMarginTTM")),
        "alpha_return_on_equity": _ratio(payload.get("ReturnOnEquityTTM")),
        "alpha_quarterly_revenue_growth_yoy": _ratio(payload.get("QuarterlyRevenueGrowthYOY")),
        "alpha_quarterly_earnings_growth_yoy": _ratio(payload.get("QuarterlyEarningsGrowthYOY")),
        "alpha_annual_dividend_per_share": _number(payload.get("DividendPerShare")),
        "alpha_dividend_yield": _ratio(payload.get("DividendYield")),
    }
    profile = {
        "alpha_name": payload.get("Name"),
        "alpha_exchange": payload.get("Exchange"),
        "alpha_sector": payload.get("Sector"),
        "alpha_industry": payload.get("Industry"),
        "alpha_fiscal_year_end": payload.get("FiscalYearEnd"),
        "alpha_latest_quarter": payload.get("LatestQuarter"),
        "alpha_dividend_date": _date_text(payload.get("DividendDate")),
        "alpha_ex_dividend_date": _date_text(payload.get("ExDividendDate")),
    }
    return {
        "availability": "available" if any(value not in (None, "") for value in [*metrics.values(), *profile.values()]) else "unavailable",
        "provider": "Alpha Vantage",
        "source": "alpha-vantage-overview",
        "source_status": meta["source_status"],
        "source_url": ALPHA_VANTAGE_BASE_URL,
        "fetched_at": meta["fetched_at"],
        "metrics": metrics,
        "profile": profile,
        "row_count": len([value for value in [*metrics.values(), *profile.values()] if value not in (None, "")]),
        "caveat": "Alpha Vantage OVERVIEW fields are free-tier supplemental fundamentals. Analyst target-price fields are intentionally excluded.",
        "data_gap": None,
        "not_financial_advice": True,
    }


def fetch_alpha_vantage_earnings(
    symbol: str,
    *,
    api_key: str | None = None,
    session: Any | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    key = api_key or get_env_var("ALPHAVANTAGE_API_KEY") or get_env_var("ALPHA_VANTAGE_API_KEY")
    if not key:
        return _missing_key("Alpha Vantage", "ALPHAVANTAGE_API_KEY", ALPHA_VANTAGE_BASE_URL, source="alpha-vantage-earnings")
    payload, meta = _fetch_json_cached(
        f"phase6a:alpha-vantage:earnings:{symbol.upper()}",
        ALPHA_VANTAGE_BASE_URL,
        provider="Alpha Vantage",
        source="alpha-vantage-earnings",
        params={"function": "EARNINGS", "symbol": symbol.upper(), "apikey": key},
        ttl_seconds=EQUITY_EARNINGS_TTL_SECONDS,
        session=session,
    )
    if payload is None:
        return _provider_gap("Alpha Vantage", ALPHA_VANTAGE_BASE_URL, source="alpha-vantage-earnings", **meta)
    rows = []
    for item in _rows(payload.get("quarterlyEarnings"))[: max(1, min(int(limit), 24))]:
        rows.append(
            {
                "symbol": symbol.upper(),
                "event_type": "reported-earnings",
                "event_date": _date_text(item.get("reportedDate")),
                "fiscal_period_end": _date_text(item.get("fiscalDateEnding")),
                "fiscal_year": None,
                "fiscal_quarter": None,
                "event_time_code": None,
                "timezone": "provider-date/timezone-unspecified",
                "reported_eps": _number(item.get("reportedEPS")),
                "estimated_eps": _number(item.get("estimatedEPS")),
                "surprise": _number(item.get("surprise")),
                "surprise_pct": _number(item.get("surprisePercentage")),
                "revenue_estimate": None,
                "revenue_actual": None,
                "provider": "Alpha Vantage",
                "source": "alpha-vantage-earnings",
                "source_url": ALPHA_VANTAGE_BASE_URL,
                "source_status": meta["source_status"],
                "fetched_at": meta["fetched_at"],
                "caveat": "Alpha Vantage reported earnings row; date is provider-supplied and timezone is unspecified.",
                "data_gap": None,
                "not_financial_advice": True,
            }
        )
    return {
        "availability": "available" if rows else "unavailable",
        "provider": "Alpha Vantage",
        "source": "alpha-vantage-earnings",
        "source_status": meta["source_status"],
        "source_url": ALPHA_VANTAGE_BASE_URL,
        "fetched_at": meta["fetched_at"],
        "rows": rows,
        "row_count": len(rows),
        "caveat": "Reported and estimated EPS are provider fields; missing values remain null.",
        "data_gap": None if rows else "Alpha Vantage returned no quarterly earnings rows.",
        "not_financial_advice": True,
    }


def fetch_alpha_vantage_news(symbol: str, *, api_key: str | None = None, session: Any | None = None, limit: int = 8) -> dict[str, Any]:
    key = api_key or get_env_var("ALPHAVANTAGE_API_KEY") or get_env_var("ALPHA_VANTAGE_API_KEY")
    if not key:
        return _missing_key("Alpha Vantage", "ALPHAVANTAGE_API_KEY", ALPHA_VANTAGE_BASE_URL, source="alpha-vantage-news")
    payload, meta = _fetch_json_cached(
        f"phase5x:alpha-vantage:news:{symbol.upper()}:{limit}",
        ALPHA_VANTAGE_BASE_URL,
        provider="Alpha Vantage",
        source="alpha-vantage-news",
        params={"function": "NEWS_SENTIMENT", "tickers": symbol.upper(), "sort": "LATEST", "limit": str(limit), "apikey": key},
        ttl_seconds=EQUITY_NEWS_TTL_SECONDS,
        session=session,
    )
    if payload is None:
        return _provider_gap("Alpha Vantage", ALPHA_VANTAGE_BASE_URL, source="alpha-vantage-news", **meta)
    rows = []
    for item in _rows(payload.get("feed"))[:limit]:
        rows.append(
            {
                "title": item.get("title"),
                "summary": item.get("summary"),
                "published_at": _alpha_time(item.get("time_published")),
                "source_url": item.get("url"),
                "provider": f"Alpha Vantage / {item.get('source') or 'news'}",
                "aggregator": "Alpha Vantage NEWS_SENTIMENT",
                "source_status": meta["source_status"],
                "fetched_at": meta["fetched_at"],
                "freshness": meta["source_status"],
                "sentiment_score": _number(item.get("overall_sentiment_score")),
                "match_terms": [symbol.upper()],
                "exact_symbol_scope": True,
                "caveat": "Provider-scoped ticker news; sentiment is a provider field and is not a recommendation.",
                "data_gap": None,
                "not_financial_advice": True,
            }
        )
    return {
        "availability": "available" if rows else "unavailable",
        "provider": "Alpha Vantage",
        "source": "alpha-vantage-news",
        "source_status": meta["source_status"],
        "source_url": ALPHA_VANTAGE_BASE_URL,
        "fetched_at": meta["fetched_at"],
        "rows": rows,
        "row_count": len(rows),
        "caveat": "Alpha Vantage NEWS_SENTIMENT rows are supplemental and publisher links remain the source of truth.",
        "data_gap": None if rows else "Alpha Vantage returned no ticker-scoped news rows.",
        "not_financial_advice": True,
    }


def fetch_finnhub_earnings_calendar(
    symbol: str,
    *,
    api_key: str | None = None,
    session: Any | None = None,
    limit: int = 12,
    today: str | date | None = None,
) -> dict[str, Any]:
    key = api_key or get_env_var("FINNHUB_API_KEY")
    source_url = f"{FINNHUB_BASE_URL}/calendar/earnings"
    if not key:
        return _missing_key("Finnhub", "FINNHUB_API_KEY", source_url, source="finnhub-earnings-calendar")
    current = _date_value(today) or datetime.now(timezone.utc).date()
    start = current - timedelta(days=45)
    end = current + timedelta(days=120)
    payload, meta = _fetch_json_cached(
        f"phase6a:finnhub:earnings-calendar:{symbol.upper()}:{current.isoformat()}",
        source_url,
        provider="Finnhub",
        source="finnhub-earnings-calendar",
        params={
            "from": start.isoformat(),
            "to": end.isoformat(),
            "symbol": symbol.upper(),
            "token": key,
        },
        ttl_seconds=EQUITY_EARNINGS_TTL_SECONDS,
        session=session,
    )
    if payload is None:
        return _provider_gap("Finnhub", source_url, source="finnhub-earnings-calendar", **meta)
    rows = []
    for item in _rows(payload.get("earningsCalendar"))[: max(1, min(int(limit), 24))]:
        actual_eps = _number(item.get("epsActual"))
        rows.append(
            {
                "symbol": str(item.get("symbol") or symbol).upper(),
                "event_type": "reported-earnings" if actual_eps is not None else "scheduled-earnings",
                "event_date": _date_text(item.get("date")),
                "fiscal_period_end": None,
                "fiscal_year": _integer(item.get("year")),
                "fiscal_quarter": _integer(item.get("quarter")),
                "event_time_code": str(item.get("hour") or "") or None,
                "timezone": "provider-date/timezone-unspecified",
                "reported_eps": actual_eps,
                "estimated_eps": _number(item.get("epsEstimate")),
                "surprise": None,
                "surprise_pct": None,
                "revenue_estimate": _number(item.get("revenueEstimate")),
                "revenue_actual": _number(item.get("revenueActual")),
                "provider": "Finnhub",
                "source": "finnhub-earnings-calendar",
                "source_url": source_url,
                "source_status": meta["source_status"],
                "fetched_at": meta["fetched_at"],
                "caveat": "Finnhub earnings calendar date/time code is provider-supplied; timezone is not asserted.",
                "data_gap": None,
                "not_financial_advice": True,
            }
        )
    return {
        "availability": "available" if rows else "unavailable",
        "provider": "Finnhub",
        "source": "finnhub-earnings-calendar",
        "source_status": meta["source_status"],
        "source_url": source_url,
        "fetched_at": meta["fetched_at"],
        "rows": rows,
        "row_count": len(rows),
        "caveat": "Calendar dates and estimates can be revised by the provider.",
        "data_gap": None if rows else "Finnhub returned no earnings calendar rows for the bounded window.",
        "not_financial_advice": True,
    }


def fetch_finnhub_profile(symbol: str, *, api_key: str | None = None, session: Any | None = None) -> dict[str, Any]:
    key = api_key or get_env_var("FINNHUB_API_KEY")
    source_url = f"{FINNHUB_BASE_URL}/stock/profile2"
    if not key:
        return _missing_key("Finnhub", "FINNHUB_API_KEY", source_url, source="finnhub-profile")
    payload, meta = _fetch_json_cached(
        f"phase5x:finnhub:profile:{symbol.upper()}",
        source_url,
        provider="Finnhub",
        source="finnhub-profile",
        params={"symbol": symbol.upper(), "token": key},
        ttl_seconds=EQUITY_BREADTH_TTL_SECONDS,
        session=session,
    )
    if payload is None:
        return _provider_gap("Finnhub", source_url, source="finnhub-profile", **meta)
    metrics = {
        "finnhub_market_cap_musd": _number(payload.get("marketCapitalization")),
        "finnhub_share_outstanding_m": _number(payload.get("shareOutstanding")),
    }
    profile = {
        "finnhub_name": payload.get("name"),
        "finnhub_ticker": payload.get("ticker"),
        "finnhub_exchange": payload.get("exchange"),
        "finnhub_industry": payload.get("finnhubIndustry"),
        "finnhub_ipo": payload.get("ipo"),
        "finnhub_weburl": payload.get("weburl"),
    }
    return {
        "availability": "available" if any(value not in (None, "") for value in [*metrics.values(), *profile.values()]) else "unavailable",
        "provider": "Finnhub",
        "source": "finnhub-profile",
        "source_status": meta["source_status"],
        "source_url": source_url,
        "fetched_at": meta["fetched_at"],
        "metrics": metrics,
        "profile": profile,
        "row_count": len([value for value in [*metrics.values(), *profile.values()] if value not in (None, "")]),
        "caveat": "Finnhub profile is supplemental free-tier company metadata.",
        "data_gap": None,
        "not_financial_advice": True,
    }


def fetch_finnhub_company_news(symbol: str, *, api_key: str | None = None, session: Any | None = None, limit: int = 8) -> dict[str, Any]:
    key = api_key or get_env_var("FINNHUB_API_KEY")
    source_url = f"{FINNHUB_BASE_URL}/company-news"
    if not key:
        return _missing_key("Finnhub", "FINNHUB_API_KEY", source_url, source="finnhub-company-news")
    today = datetime.now(timezone.utc).date()
    payload, meta = _fetch_json_cached(
        f"phase5x:finnhub:company-news:{symbol.upper()}:{today.isoformat()}",
        source_url,
        provider="Finnhub",
        source="finnhub-company-news",
        params={"symbol": symbol.upper(), "from": (today - timedelta(days=14)).isoformat(), "to": today.isoformat(), "token": key},
        ttl_seconds=EQUITY_NEWS_TTL_SECONDS,
        session=session,
    )
    if payload is None:
        return _provider_gap("Finnhub", source_url, source="finnhub-company-news", **meta)
    rows = []
    for item in _rows(payload)[:limit]:
        rows.append(
            {
                "title": item.get("headline"),
                "summary": item.get("summary"),
                "published_at": _unix_time(item.get("datetime")),
                "source_url": item.get("url"),
                "provider": f"Finnhub / {item.get('source') or 'company-news'}",
                "aggregator": "Finnhub company-news",
                "source_status": meta["source_status"],
                "fetched_at": meta["fetched_at"],
                "freshness": meta["source_status"],
                "category": item.get("category"),
                "match_terms": [symbol.upper()],
                "exact_symbol_scope": True,
                "caveat": "Finnhub company-news is company-scoped provider output; verify at the linked publisher.",
                "data_gap": None,
                "not_financial_advice": True,
            }
        )
    return {
        "availability": "available" if rows else "unavailable",
        "provider": "Finnhub",
        "source": "finnhub-company-news",
        "source_status": meta["source_status"],
        "source_url": source_url,
        "fetched_at": meta["fetched_at"],
        "rows": rows,
        "row_count": len(rows),
        "caveat": "Finnhub company-news rows are supplemental free-tier headlines.",
        "data_gap": None if rows else "Finnhub returned no company-news rows for the requested window.",
        "not_financial_advice": True,
    }


def _fetch_json_cached(
    cache_key: str,
    source_url: str,
    *,
    provider: str,
    source: str,
    params: dict[str, Any],
    ttl_seconds: int,
    session: Any | None = None,
    timeout: int = 15,
) -> tuple[Any | None, dict[str, Any]]:
    now = datetime.now(timezone.utc)
    cached = load_runtime_cache_record(cache_key)
    if cached and cached.is_fresh(ttl_seconds, now):
        return cached.data, {"source_status": "cached", "fetched_at": cached.fetched_at_iso, "data_gap": None}
    client = session or requests
    if client is None:
        if cached and cached.age_seconds(now) <= EQUITY_STALE_SECONDS:
            return cached.data, {"source_status": "stale", "fetched_at": cached.fetched_at_iso, "data_gap": "requests is unavailable; using stale cached provider data."}
        return None, {"source_status": "unavailable", "fetched_at": now.isoformat(), "data_gap": "requests is unavailable and no cached provider data exists."}
    try:
        response = client.get(source_url, params=params, timeout=timeout)
        status_code = int(getattr(response, "status_code", 0) or 0)
        if status_code in {401, 403}:
            raise PermissionError(f"{status_code} unauthorized or subscription blocked")
        if status_code == 429:
            raise RuntimeError("429 rate limited")
        response.raise_for_status()
        payload = response.json()
        issue = _provider_payload_issue(payload)
        if issue:
            if cached and cached.age_seconds(now) <= EQUITY_STALE_SECONDS:
                return cached.data, {"source_status": "stale", "fetched_at": cached.fetched_at_iso, "data_gap": f"Live provider response was rejected; stale cache retained. {issue}"}
            status = "rate-limited" if "rate" in issue.lower() or "frequency" in issue.lower() else "provider-error"
            return None, {"source_status": status, "fetched_at": now.isoformat(), "data_gap": issue}
        record = RuntimeCacheRecord(cache_key, payload, source=source, provider=provider, source_url=source_url, fetched_at=now)
        save_runtime_cache_record(record)
        return payload, {"source_status": "live/fresh", "fetched_at": record.fetched_at_iso, "data_gap": None}
    except Exception as exc:
        if cached and cached.age_seconds(now) <= EQUITY_STALE_SECONDS:
            return cached.data, {"source_status": "stale", "fetched_at": cached.fetched_at_iso, "data_gap": f"Live provider refresh failed; stale cache retained. {exc}"}
        status = "rate-limited" if "429" in str(exc) else "provider-error"
        return None, {"source_status": status, "fetched_at": now.isoformat(), "data_gap": str(exc)}


def _provider_payload_issue(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("Note", "Information", "Error Message"):
            if payload.get(key):
                return str(payload[key])
    return None


def _source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": row.get("provider"),
        "source": row.get("source"),
        "source_url": row.get("source_url"),
        "source_status": row.get("source_status"),
        "fetched_at": row.get("fetched_at"),
        "row_count": row.get("row_count", len(_rows(row.get("rows")))),
        "caveat": row.get("caveat"),
        "data_gap": row.get("data_gap"),
        "not_financial_advice": True,
    }


def _missing_key(provider: str, env_var: str, source_url: str, *, source: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "availability": "provider-required",
        "provider": provider,
        "source": source,
        "source_status": "missing-key",
        "source_url": source_url,
        "fetched_at": now,
        "metrics": {},
        "profile": {},
        "rows": [],
        "row_count": 0,
        "caveat": f"{provider} is optional and free-tier capable; configure {env_var} to enable this panel.",
        "data_gap": f"Missing optional environment variable: {env_var}.",
        "not_financial_advice": True,
    }


def _provider_gap(provider: str, source_url: str, *, source: str, source_status: str, fetched_at: str, data_gap: str | None) -> dict[str, Any]:
    return {
        "availability": "unavailable",
        "provider": provider,
        "source": source,
        "source_status": source_status,
        "source_url": source_url,
        "fetched_at": fetched_at,
        "metrics": {},
        "profile": {},
        "rows": [],
        "row_count": 0,
        "caveat": f"{provider} did not return a usable free-tier response for this request.",
        "data_gap": data_gap,
        "not_financial_advice": True,
    }


def _not_applicable(reason: str) -> dict[str, Any]:
    return {
        "availability": "not_applicable",
        "provider": "not_applicable",
        "source_status": "not_applicable",
        "source_url": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {},
        "profile": {},
        "provider_rows": [],
        "source_register": [],
        "rows": [],
        "caveat": reason,
        "data_gap": None,
        "not_financial_advice": True,
    }


def _combined_status(rows: list[dict[str, Any]]) -> str:
    statuses = [str(row.get("source_status") or "") for row in rows]
    for status in ("live/fresh", "cached", "stale", "rate-limited", "provider-error", "missing-key"):
        if status in statuses:
            return status
    return statuses[0] if statuses else "unavailable"


def _latest_fetched_at(rows: list[dict[str, Any]]) -> str | None:
    values = [str(row.get("fetched_at")) for row in rows if row.get("fetched_at")]
    return sorted(values)[-1] if values else None


def _dedupe_news(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output = []
    for row in sorted(rows, key=lambda item: str(item.get("published_at") or ""), reverse=True):
        key = str(row.get("source_url") or row.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(row)
        if len(output) >= limit:
            break
    return output


def _dedupe_earnings(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    output = []
    for row in sorted(
        rows,
        key=lambda item: (str(item.get("event_date") or ""), str(item.get("provider") or "")),
        reverse=True,
    ):
        key = (
            str(row.get("provider") or ""),
            str(row.get("event_type") or ""),
            str(row.get("event_date") or row.get("fiscal_period_end") or ""),
        )
        if not key[2] or key in seen:
            continue
        seen.add(key)
        output.append(row)
        if len(output) >= limit:
            break
    return output


def _rows(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _symbol(identity: dict[str, Any]) -> str:
    return str(identity.get("provider_symbol") or identity.get("symbol") or "").upper()


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _ratio(value: Any) -> float | None:
    return _number(value)


def _integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError):
        return None


def _date_text(value: Any) -> str | None:
    current = _date_value(value)
    return current.isoformat() if current else None


def _alpha_time(value: Any) -> str | None:
    raw = str(value or "")
    if len(raw) >= 15:
        try:
            return datetime.strptime(raw[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            return None
    return None


def _unix_time(value: Any) -> str | None:
    number = _number(value)
    if number is None:
        return None
    try:
        return datetime.fromtimestamp(number, tz=timezone.utc).isoformat()
    except Exception:
        return None
