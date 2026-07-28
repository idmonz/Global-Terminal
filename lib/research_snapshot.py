from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


RESEARCH_SNAPSHOT_VERSION = "research_snapshot.v1"
MAX_RESEARCH_SYMBOLS = 5
MAX_RESEARCH_PROVIDER_CALLS = 16
RESEARCH_SNAPSHOT_TTL_SECONDS = 900

ProviderFetcher = Callable[[str], dict[str, Any]]


def research_snapshot_cache_key(asset_class: str, symbol: str) -> str:
    return f"phase6f:research-snapshot:{str(asset_class).lower()}:{str(symbol).upper()}"


def default_provider_budget(*, max_symbols: int = MAX_RESEARCH_SYMBOLS) -> dict[str, Any]:
    bounded = max(1, min(int(max_symbols), MAX_RESEARCH_SYMBOLS))
    planned = {
        "yfinance:multi-history": 1,
        "alpha-vantage:overview": bounded,
        "finnhub:earnings-calendar": bounded,
        "finnhub:company-news": bounded,
    }
    return {
        "maximum_symbols": bounded,
        "maximum_concurrency": 1,
        "maximum_calls": sum(planned.values()),
        "planned_calls": planned,
        "actual_calls": 0,
        "actual_calls_by_operation": {key: 0 for key in planned},
        "cache_hits": 0,
        "stale_hits": 0,
        "failed_calls": 0,
        "blocked_calls": 0,
        "skipped_calls": 0,
        "rate_limit_class": "free-first-bounded",
        "timeout_seconds": 15,
        "ttl_seconds": RESEARCH_SNAPSHOT_TTL_SECONDS,
        "next_safe_refresh_at": None,
    }


def build_research_snapshot_rows(
    identities: list[dict[str, Any]],
    history_by_symbol: dict[str, list[dict[str, Any]]],
    *,
    overview_fetcher: ProviderFetcher,
    earnings_fetcher: ProviderFetcher,
    news_fetcher: ProviderFetcher,
    previous_rows: dict[str, dict[str, Any]] | None = None,
    history_call_count: int = 0,
    max_symbols: int = MAX_RESEARCH_SYMBOLS,
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    bounded = [
        row
        for row in identities
        if isinstance(row, dict) and row.get("symbol")
    ][: max(1, min(int(max_symbols), MAX_RESEARCH_SYMBOLS))]
    budget = default_provider_budget(max_symbols=len(bounded) or 1)
    history_calls = max(0, min(int(history_call_count), 1))
    budget["actual_calls"] = history_calls
    budget["actual_calls_by_operation"]["yfinance:multi-history"] = history_calls
    prior = previous_rows or {}
    rows: list[dict[str, Any]] = []

    for identity in bounded:
        symbol = str(identity["symbol"]).upper()
        history = [
            row for row in history_by_symbol.get(symbol, []) if isinstance(row, dict)
        ]
        overview = _call_provider(
            overview_fetcher,
            symbol,
            operation="alpha-vantage:overview",
            budget=budget,
        )
        earnings = _call_provider(
            earnings_fetcher,
            symbol,
            operation="finnhub:earnings-calendar",
            budget=budget,
        )
        news = _call_provider(
            news_fetcher,
            symbol,
            operation="finnhub:company-news",
            budget=budget,
        )
        current = _build_row(
            identity,
            history,
            overview=overview,
            earnings=earnings,
            news=news,
            generated_at=generated_at,
        )
        merged, stale_sections = _retain_last_known_good(
            current,
            prior.get(symbol),
        )
        budget["stale_hits"] += stale_sections
        rows.append(_public_only(merged))

    budget["actual_calls"] = min(
        int(budget["actual_calls"]),
        int(budget["maximum_calls"]),
    )
    budget["next_safe_refresh_at"] = (
        generated_at + timedelta(seconds=RESEARCH_SNAPSHOT_TTL_SECONDS)
    ).isoformat()
    enriched_count = sum(
        1
        for row in rows
        if row.get("quote", {}).get("last_price") is not None
        and (
            row.get("financials", {}).get("availability") == "available"
            or bool(row.get("catalysts", {}).get("earnings"))
            or bool(row.get("catalysts", {}).get("dividends"))
            or bool(row.get("catalysts", {}).get("news"))
        )
    )
    return {
        "research_snapshot_version": RESEARCH_SNAPSHOT_VERSION,
        "generated_at": generated_at.isoformat(),
        "rows": rows,
        "provider_budget": budget,
        "summary": {
            "requested_count": len(bounded),
            "completed_count": len(rows),
            "enriched_count": enriched_count,
            "failed_count": sum(row.get("status") == "failed" for row in rows),
            "stale_count": sum(row.get("source_status") == "stale" for row in rows),
            "not_financial_advice": True,
        },
        "caveat": (
            "Bounded free-first research snapshot. Provider dates and delayed "
            "market observations must be verified at the linked source."
        ),
        "not_financial_advice": True,
    }


def _call_provider(
    fetcher: ProviderFetcher,
    symbol: str,
    *,
    operation: str,
    budget: dict[str, Any],
) -> dict[str, Any]:
    if budget["actual_calls"] >= budget["maximum_calls"]:
        budget["blocked_calls"] += 1
        return _gap(
            operation.split(":", 1)[0],
            "budget-exhausted",
            "Provider call budget was exhausted before this operation.",
        )
    try:
        result = fetcher(symbol)
    except Exception as exc:
        budget["actual_calls"] += 1
        budget["actual_calls_by_operation"][operation] += 1
        budget["failed_calls"] += 1
        return _gap(
            operation.split(":", 1)[0],
            "provider-error",
            f"Provider refresh failed: {type(exc).__name__}.",
        )
    normalized = dict(result) if isinstance(result, dict) else _gap(
        operation.split(":", 1)[0],
        "provider-error",
        "Provider returned a non-object response.",
    )
    status = str(normalized.get("source_status") or "unavailable")
    if status == "cached":
        budget["cache_hits"] += 1
    elif status in {"missing-key", "not_applicable", "budget-exhausted"}:
        budget["skipped_calls"] += 1
    else:
        budget["actual_calls"] += 1
        budget["actual_calls_by_operation"][operation] += 1
        if status in {"rate-limited", "provider-error", "forbidden", "unavailable"}:
            budget["failed_calls"] += 1
    return normalized


def _build_row(
    identity: dict[str, Any],
    history: list[dict[str, Any]],
    *,
    overview: dict[str, Any],
    earnings: dict[str, Any],
    news: dict[str, Any],
    generated_at: datetime,
) -> dict[str, Any]:
    from .watchlist_desk import compute_watchlist_advanced_metrics

    symbol = str(identity["symbol"]).upper()
    advanced = compute_watchlist_advanced_metrics(history)
    quote = _quote(history, generated_at)
    financials = _financials(overview)
    catalysts = _catalysts(symbol, overview, earnings, news, as_of=generated_at)
    sources = [
        _source_row(overview),
        _source_row(earnings),
        _source_row(news),
    ]
    source_status = _combined_status(
        [quote.get("source_status"), financials.get("source_status"), catalysts.get("source_status")]
    )
    gaps = [
        quote.get("data_gap"),
        financials.get("data_gap"),
        catalysts.get("data_gap"),
    ]
    status = (
        "fresh"
        if source_status in {"live/fresh", "cached"}
        and quote.get("last_price") is not None
        else "stale"
        if source_status == "stale"
        else "partial"
        if quote.get("last_price") is not None
        else "failed"
    )
    return {
        "research_snapshot_version": RESEARCH_SNAPSHOT_VERSION,
        "symbol": symbol,
        "identity": {
            "symbol": symbol,
            "name": identity.get("name"),
            "asset_class": identity.get("asset_class"),
            "exchange": identity.get("exchange"),
            "mic": identity.get("mic"),
            "sector": identity.get("sector"),
            "industry": identity.get("industry"),
            "identity_status": "exact",
        },
        "status": status,
        "source_status": source_status,
        "fetched_at": generated_at.isoformat(),
        "quote": quote,
        "performance": {
            key: advanced.get(key)
            for key in (
                "status",
                "observation_count",
                "return_1w_pct",
                "return_1m_pct",
                "return_3m_pct",
                "average_volume_10",
                "data_gap",
            )
        },
        "risk": {
            "realized_volatility_1m_pct": advanced.get("realized_volatility_1m_pct"),
            "data_gap": advanced.get("data_gap"),
            "formula_version": advanced.get("formula_version"),
        },
        "technicals": {
            key: advanced.get(key)
            for key in ("rsi_14", "sma_20", "sma_50", "trend_state", "formula_version", "data_gap")
        },
        "financials": financials,
        "catalysts": catalysts,
        "source_register": [row for row in sources if row.get("provider")],
        "confidence": "medium" if status in {"fresh", "stale"} else "low",
        "data_gap": "; ".join(str(gap) for gap in gaps if gap) or None,
        "not_financial_advice": True,
    }


def _quote(history: list[dict[str, Any]], generated_at: datetime) -> dict[str, Any]:
    closes = [
        _number(row.get("close"))
        for row in history
        if _number(row.get("close")) is not None
    ]
    last = closes[-1] if closes else None
    previous = closes[-2] if len(closes) > 1 else None
    change = last - previous if last is not None and previous is not None else None
    change_pct = (
        change / previous * 100
        if change is not None and previous not in (None, 0)
        else None
    )
    last_row = history[-1] if history else {}
    return {
        "last_price": last,
        "change": round(change, 6) if change is not None else None,
        "change_pct": round(change_pct, 6) if change_pct is not None else None,
        "volume": _number(last_row.get("volume")),
        "market_data_as_of": last_row.get("date"),
        "retrieved_at": generated_at.isoformat(),
        "provider": "yfinance",
        "source_url": None,
        "source_status": "cached" if history else "unavailable",
        "data_gap": None if history else "No exact-symbol history was available.",
    }


def _financials(overview: dict[str, Any]) -> dict[str, Any]:
    metrics = overview.get("metrics") if isinstance(overview.get("metrics"), dict) else {}
    canonical = {
        "market_cap": _number(metrics.get("alpha_market_cap")),
        "revenue_ttm": _number(metrics.get("alpha_revenue_ttm")),
        "eps": _number(metrics.get("alpha_eps")),
        "pe_ratio": _number(metrics.get("alpha_pe_ratio")),
        "annual_dividend_per_share": _number(metrics.get("alpha_annual_dividend_per_share")),
        "dividend_yield": _number(metrics.get("alpha_dividend_yield")),
    }
    available = any(value is not None for value in canonical.values())
    return {
        "availability": "available" if available else "unavailable",
        "provider": overview.get("provider"),
        "source_url": overview.get("source_url"),
        "source_status": overview.get("source_status") or "unavailable",
        "fetched_at": overview.get("fetched_at"),
        "metrics": canonical,
        "caveat": overview.get("caveat"),
        "data_gap": overview.get("data_gap") if not available else None,
        "not_financial_advice": True,
    }


def _catalysts(
    symbol: str,
    overview: dict[str, Any],
    earnings: dict[str, Any],
    news: dict[str, Any],
    *,
    as_of: datetime,
) -> dict[str, Any]:
    earnings_rows = [
        {**row, "symbol": symbol}
        for row in _records(earnings.get("rows"))
        if str(row.get("symbol") or symbol).upper() == symbol
    ][:6]
    profile = overview.get("profile") if isinstance(overview.get("profile"), dict) else {}
    metrics = overview.get("metrics") if isinstance(overview.get("metrics"), dict) else {}
    dividends = []
    if profile.get("alpha_dividend_date") or profile.get("alpha_ex_dividend_date"):
        dividends.append(
            {
                "symbol": symbol,
                "event_type": "dividend",
                "payment_date": profile.get("alpha_dividend_date"),
                "ex_dividend_date": profile.get("alpha_ex_dividend_date"),
                "amount": _number(metrics.get("alpha_annual_dividend_per_share")),
                "yield": _number(metrics.get("alpha_dividend_yield")),
                "provider": overview.get("provider"),
                "source_url": overview.get("source_url"),
                "source_status": overview.get("source_status"),
                "fetched_at": overview.get("fetched_at"),
                "caveat": "Annual dividend fields and provider dates are supplemental and can be revised.",
                "not_financial_advice": True,
            }
        )
    news_rows = []
    for row in _records(news.get("rows")):
        if not row.get("exact_symbol_scope"):
            continue
        terms = [
            str(term).upper()
            for term in row.get("match_terms", [])
            if str(term).strip()
        ]
        if symbol not in terms:
            continue
        news_rows.append(
            {
                **row,
                "match_evidence": {
                    "symbol": symbol,
                    "scope": "provider-company-news",
                    "exact": True,
                    "terms": terms,
                },
            }
        )
        if len(news_rows) >= 5:
            break
    statuses = [
        overview.get("source_status"),
        earnings.get("source_status"),
        news.get("source_status"),
    ]
    gaps = [
        earnings.get("data_gap"),
        news.get("data_gap"),
    ]
    return {
        "symbol": symbol,
        "availability": "available" if earnings_rows or dividends or news_rows else "unavailable",
        "source_status": _combined_status(statuses),
        "earnings": earnings_rows,
        "dividends": dividends,
        "news": news_rows,
        "next_event": _next_event(earnings_rows, dividends, as_of=as_of),
        "caveat": "Catalysts are informational provider events, not alerts or trading signals.",
        "data_gap": "; ".join(str(gap) for gap in gaps if gap) or None,
        "not_financial_advice": True,
    }


def _next_event(
    earnings: list[dict[str, Any]],
    dividends: list[dict[str, Any]],
    *,
    as_of: datetime,
) -> dict[str, Any] | None:
    candidates = [
        {**row, "_date": row.get("event_date")}
        for row in earnings
        if row.get("event_date")
    ]
    candidates.extend(
        {**row, "_date": row.get("ex_dividend_date") or row.get("payment_date")}
        for row in dividends
        if row.get("ex_dividend_date") or row.get("payment_date")
    )
    if not candidates:
        return None
    current_date = as_of.date().isoformat()
    future = [row for row in candidates if str(row.get("_date")) >= current_date]
    if future:
        selected = min(future, key=lambda row: str(row.get("_date")))
        timing = "upcoming"
    else:
        selected = max(candidates, key=lambda row: str(row.get("_date")))
        timing = "recent"
    return {
        **{key: value for key, value in selected.items() if key != "_date"},
        "event_timing": timing,
    }


def _retain_last_known_good(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> tuple[dict[str, Any], int]:
    if not isinstance(previous, dict):
        return current, 0
    merged = deepcopy(current)
    stale_sections = 0
    for section in ("financials", "catalysts"):
        active = merged.get(section) if isinstance(merged.get(section), dict) else {}
        prior = previous.get(section) if isinstance(previous.get(section), dict) else {}
        if active.get("availability") == "available" or prior.get("availability") != "available":
            continue
        gap = active.get("data_gap") or "Current provider refresh returned no usable values."
        merged[section] = {
            **deepcopy(prior),
            "source_status": "stale",
            "data_gap": f"Last-known-good retained after refresh failure. {gap}",
        }
        stale_sections += 1
    if stale_sections:
        merged["status"] = "stale"
        merged["source_status"] = "stale"
        current_gap = str(current.get("data_gap") or "")
        merged["data_gap"] = (
            f"Last-known-good retained. {current_gap}".strip()
        )
    return merged, stale_sections


def _source_row(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": value.get("provider"),
        "source": value.get("source"),
        "source_url": value.get("source_url"),
        "source_status": value.get("source_status"),
        "fetched_at": value.get("fetched_at"),
        "row_count": value.get("row_count") or len(_records(value.get("rows"))),
        "caveat": value.get("caveat"),
        "data_gap": value.get("data_gap"),
        "not_financial_advice": True,
    }


def _combined_status(statuses: list[Any]) -> str:
    normalized = {str(status or "unavailable") for status in statuses}
    for status in (
        "live/fresh",
        "cached",
        "stale",
        "rate-limited",
        "provider-error",
        "missing-key",
        "unavailable",
    ):
        if status in normalized:
            return status
    return "unavailable"


def _gap(provider: str, status: str, reason: str) -> dict[str, Any]:
    return {
        "availability": "unavailable",
        "provider": provider,
        "source_status": status,
        "source_url": None,
        "fetched_at": None,
        "metrics": {},
        "profile": {},
        "rows": [],
        "caveat": "No provider value is synthesized.",
        "data_gap": reason,
        "not_financial_advice": True,
    }


def _public_only(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _public_only(item)
            for key, item in value.items()
            if key not in {"private_reason", "watch_reason", "notes", "private_notes"}
        }
    if isinstance(value, list):
        return [_public_only(item) for item in value]
    return value


def _records(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None
