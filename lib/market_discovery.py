from __future__ import annotations

import math
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Iterable

try:
    import yfinance as yf
    from yfinance import EquityQuery
    from yfinance.const import SECTOR_INDUSTY_MAPPING
except Exception:  # pragma: no cover - optional provider
    yf = None
    EquityQuery = None
    SECTOR_INDUSTY_MAPPING = {}


DISCOVERY_VERSION = "market_discovery.v1"
FINANCIAL_SNAPSHOT_VERSION = "yahoo_screener_snapshot.v1"
MARKET_SNAPSHOT_VERSION = "yahoo_us_market_snapshot.v2"
SECTOR_CLASSIFICATION_VERSION = "yahoo_sector_classification.v2"
YAHOO_SECTORS = tuple(SECTOR_INDUSTY_MAPPING) or (
    "Basic Materials",
    "Communication Services",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Energy",
    "Financial Services",
    "Healthcare",
    "Industrials",
    "Real Estate",
    "Technology",
    "Utilities",
)
PROJECT_SECTOR_MAP = {
    "Basic Materials": "Materials",
    "Communication Services": "Communication Services",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Energy": "Energy",
    "Financial Services": "Financials",
    "Healthcare": "Health Care",
    "Industrials": "Industrials",
    "Real Estate": "Real Estate",
    "Technology": "Information Technology",
    "Utilities": "Utilities",
}
_FINANCIAL_TTL_SECONDS = 21_600
_FINANCIAL_LOCK = threading.Lock()
_FINANCIAL_CACHE: dict[str, dict[str, Any]] = {}
_SECTOR_CACHE: dict[str, dict[str, Any]] = {}
_monotonic = time.monotonic

_TECHNICAL_FIELDS = (
    "return_1d_pct",
    "return_1m_pct",
    "realized_volatility_pct",
    "drawdown_pct",
    "rsi",
    "price_vs_sma20_pct",
    "volume_zscore",
)
_FINANCIAL_FIELDS = (
    "market_cap",
    "trailing_pe",
    "forward_pe",
    "price_to_book",
    "eps_ttm",
    "eps_forward",
)

RANK_MODEL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "balanced": {
        "label": "Balanced",
        "version": "balanced.v1",
        "description": "Momentum, risk, trend, valuation, and completeness with no missing-value imputation.",
        "required_factors": [
            "return_1m_pct",
            "realized_volatility_pct",
            "drawdown_pct",
            "price_vs_sma20_pct",
            "trailing_pe",
            "data_quality_score",
        ],
        "components": [
            ("return_1m_pct", 0.30, "high"),
            ("realized_volatility_pct", 0.20, "low"),
            ("drawdown_pct", 0.15, "high"),
            ("price_vs_sma20_pct", 0.15, "high"),
            ("trailing_pe", 0.15, "low"),
            ("data_quality_score", 0.05, "high"),
        ],
    },
    "momentum": {
        "label": "Momentum",
        "version": "momentum.v1",
        "description": "Recent return, trend, RSI position, and relative volume.",
        "required_factors": [
            "return_1m_pct",
            "return_1d_pct",
            "price_vs_sma20_pct",
            "rsi",
            "volume_zscore",
        ],
        "components": [
            ("return_1m_pct", 0.45, "high"),
            ("return_1d_pct", 0.15, "high"),
            ("price_vs_sma20_pct", 0.20, "high"),
            ("rsi", 0.10, "target55"),
            ("volume_zscore", 0.10, "high"),
        ],
    },
    "risk_adjusted": {
        "label": "Risk adjusted",
        "version": "risk_adjusted.v1",
        "description": "One-month return balanced by realized volatility and drawdown resilience.",
        "required_factors": ["return_1m_pct", "realized_volatility_pct", "drawdown_pct"],
        "components": [
            ("return_1m_pct", 0.45, "high"),
            ("realized_volatility_pct", 0.35, "low"),
            ("drawdown_pct", 0.20, "high"),
        ],
    },
    "quality": {
        "label": "Financial coverage",
        "version": "quality_proxy.v1",
        "description": "Public-data valuation, positive EPS, capitalization, and completeness proxy; not intrinsic quality.",
        "required_factors": ["trailing_pe", "price_to_book", "eps_ttm", "market_cap", "data_quality_score"],
        "components": [
            ("trailing_pe", 0.25, "low"),
            ("price_to_book", 0.20, "low"),
            ("eps_ttm", 0.20, "positive"),
            ("market_cap", 0.15, "high"),
            ("data_quality_score", 0.20, "high"),
        ],
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _cache_key(symbols: Iterable[str]) -> str:
    provider_identity = id(getattr(yf, "screen", None))
    return f"{FINANCIAL_SNAPSHOT_VERSION}:{provider_identity}:{','.join(sorted(set(symbols)))}"


def _market_time(value: Any) -> str | None:
    number = _number(value)
    if number is None:
        return None
    try:
        return datetime.fromtimestamp(number, tz=timezone.utc).replace(microsecond=0).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def fetch_yahoo_us_market_snapshot(
    *,
    limit: int = 250,
    page_size: int = 250,
    minimum_market_cap: int = 500_000_000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bounded_limit = max(1, min(int(limit), 750))
    bounded_page_size = max(1, min(int(page_size), 250))
    fetched_at = _now_iso()
    if yf is None or EquityQuery is None:
        return [], {
            "provider": "yahoo-screener",
            "source_status": "unavailable",
            "fetched_at": fetched_at,
            "error": "yfinance screener support is unavailable.",
            "row_count": 0,
        }

    provider_identity = id(getattr(yf, "screen", None))
    key = f"{MARKET_SNAPSHOT_VERSION}:{provider_identity}:{bounded_limit}"
    now = _monotonic()
    with _FINANCIAL_LOCK:
        cached = _FINANCIAL_CACHE.get(key)
        if cached and now - cached["stored_at"] <= _FINANCIAL_TTL_SECONDS:
            rows = deepcopy(cached["rows"])
            for row in rows:
                row["source_status"] = "cached"
                row["financial_source_status"] = "cached"
            return rows, {**cached["status"], "source_status": "cached", "cached": True}

        try:
            query = EquityQuery(
                "and",
                [
                    EquityQuery("eq", ["region", "us"]),
                    EquityQuery("gte", ["intradaymarketcap", max(1, int(minimum_market_cap))]),
                ],
            )
            quotes: list[dict[str, Any]] = []
            provider_call_count = 0
            for offset in range(0, bounded_limit, bounded_page_size):
                size = min(bounded_page_size, bounded_limit - offset)
                kwargs = {"size": size, "sortField": "intradaymarketcap", "sortAsc": False}
                if offset:
                    kwargs["offset"] = offset
                response = yf.screen(query, **kwargs)
                provider_call_count += 1
                page = list((response or {}).get("quotes") or [])
                quotes.extend(row for row in page[:size] if isinstance(row, dict))
                if len(page) < size:
                    break
            rows = []
            seen: set[str] = set()
            for quote_row in quotes:
                symbol = str(quote_row.get("symbol") or "").upper().strip().replace(".", "-")
                if not symbol or symbol in seen:
                    continue
                seen.add(symbol)
                volume = _number(quote_row.get("regularMarketVolume"))
                average_volume = _number(quote_row.get("averageDailyVolume3Month"))
                relative_volume = (
                    round(volume / average_volume, 4)
                    if volume is not None and average_volume not in {None, 0.0}
                    else None
                )
                rows.append(
                    {
                        "symbol": symbol,
                        "name": quote_row.get("longName") or quote_row.get("shortName") or symbol,
                        "asset_class": "etf" if str(quote_row.get("quoteType") or "").upper() == "ETF" else "equity",
                        "exchange": quote_row.get("fullExchangeName") or quote_row.get("exchange"),
                        "region": quote_row.get("region") or "United States",
                        "currency": quote_row.get("currency"),
                        "market_cap": _number(quote_row.get("marketCap")),
                        "price": _number(quote_row.get("regularMarketPrice")),
                        "return_1d_pct": _number(quote_row.get("regularMarketChangePercent")),
                        "volume": volume,
                        "average_volume_3m": average_volume,
                        "relative_volume": relative_volume,
                        "market_data_as_of": _market_time(quote_row.get("regularMarketTime")),
                        "trailing_pe": _number(quote_row.get("trailingPE")),
                        "forward_pe": _number(quote_row.get("forwardPE")),
                        "price_to_book": _number(quote_row.get("priceToBook")),
                        "eps_ttm": _number(quote_row.get("epsTrailingTwelveMonths")),
                        "eps_forward": _number(quote_row.get("epsForward")),
                        "dividend_yield": _number(quote_row.get("trailingAnnualDividendYield")),
                        "provider": "yahoo-screener",
                        "source_url": f"https://finance.yahoo.com/quote/{symbol}",
                        "fetched_at": fetched_at,
                        "source_status": "live/fresh",
                        "financial_provider": "yahoo-screener",
                        "financial_source_url": f"https://finance.yahoo.com/quote/{symbol}",
                        "financial_fetched_at": fetched_at,
                        "financial_source_status": "live/fresh",
                        "exchange_delay_minutes": _number(quote_row.get("exchangeDataDelayedBy")),
                        "financial_caveat": "Public Yahoo screener snapshot; field coverage and delay vary by listing.",
                    }
                )
            status = {
                "provider": "yahoo-screener",
                "source": "Yahoo Finance public equity screener",
                "source_url": "https://finance.yahoo.com/research-hub/screener/",
                "source_status": "live/fresh",
                "freshness": "fresh retrieval / exchange-delayed fields",
                "fetched_at": fetched_at,
                "row_count": len(rows),
                "requested_limit": bounded_limit,
                "page_size": bounded_page_size,
                "page_count": provider_call_count,
                "provider_call_count": provider_call_count,
                "minimum_market_cap": max(1, int(minimum_market_cap)),
                "cached": False,
                "error": None,
                "caveat": "One delayed public Yahoo screener batch, sorted by intraday market capitalization.",
                "data_gap": None if rows else "The public screener returned no usable US equity observations.",
            }
            _FINANCIAL_CACHE[key] = {"stored_at": now, "rows": deepcopy(rows), "status": deepcopy(status)}
            return rows, status
        except Exception as exc:
            if cached:
                rows = deepcopy(cached["rows"])
                for row in rows:
                    row["source_status"] = "stale"
                    row["financial_source_status"] = "stale"
                    row["financial_caveat"] = f"{row.get('financial_caveat', '')} Refresh failed; stale snapshot retained.".strip()
                return rows, {
                    **cached["status"],
                    "source_status": "stale",
                    "freshness": "stale",
                    "cached": True,
                    "error": type(exc).__name__,
                    "data_gap": "Batch financial refresh failed; stale snapshot retained.",
                }
            return [], {
                "provider": "yahoo-screener",
                "source": "Yahoo Finance public equity screener",
                "source_status": "unavailable",
                "freshness": "unavailable",
                "fetched_at": fetched_at,
                "row_count": 0,
                "requested_limit": bounded_limit,
                "page_size": bounded_page_size,
                "page_count": 0,
                "provider_call_count": 0,
                "cached": False,
                "error": type(exc).__name__,
                "caveat": "Existing batched history remains usable when the broad public screener is unavailable.",
                "data_gap": "Broad quote and financial snapshot fields are unavailable.",
            }


def fetch_yahoo_sector_classification(
    symbols: Iterable[str],
    *,
    per_sector_limit: int = 250,
    minimum_market_cap: int = 500_000_000,
) -> dict[str, Any]:
    requested = sorted(
        {
            str(symbol or "").upper().strip().replace(".", "-")
            for symbol in symbols
            if str(symbol or "").strip()
        }
    )
    fetched_at = _now_iso()
    if not requested or yf is None or EquityQuery is None:
        return {
            "classification_version": SECTOR_CLASSIFICATION_VERSION,
            "rows": [],
            "sources": [],
            "summary": {
                "requested_count": len(requested),
                "classified_count": 0,
                "unclassified_count": len(requested),
                "provider_call_count": 0,
                "source_status": "unavailable",
                "taxonomy_authoritative": False,
            },
        }
    provider_identity = id(getattr(yf, "screen", None))
    key = f"{SECTOR_CLASSIFICATION_VERSION}:{provider_identity}:{max(1, int(minimum_market_cap))}:{max(1, min(int(per_sector_limit), 250))}"
    now = _monotonic()
    with _FINANCIAL_LOCK:
        cached = _SECTOR_CACHE.get(key)
        if cached and now - cached["stored_at"] <= _FINANCIAL_TTL_SECONDS:
            all_rows = deepcopy(cached["rows"])
            rows = [row for row in all_rows if row["symbol"] in set(requested)]
            for row in rows:
                row["source_status"] = "cached/provider-classification"
            return {
                "classification_version": SECTOR_CLASSIFICATION_VERSION,
                "rows": rows,
                "sources": deepcopy(cached["sources"]),
                "summary": {
                    **cached["summary"],
                    "requested_count": len(requested),
                    "classified_count": len(rows),
                    "unclassified_count": len(requested) - len(rows),
                    "source_status": "cached",
                },
            }
        classified: dict[str, dict[str, Any]] = {}
        sources: list[dict[str, Any]] = []
        provider_call_count = 0
        for sector in YAHOO_SECTORS:
            try:
                query = EquityQuery(
                    "and",
                    [
                        EquityQuery("eq", ["region", "us"]),
                        EquityQuery("eq", ["sector", sector]),
                        EquityQuery("gte", ["intradaymarketcap", max(1, int(minimum_market_cap))]),
                    ],
                )
                response = yf.screen(
                    query,
                    size=max(1, min(int(per_sector_limit), 250)),
                    sortField="intradaymarketcap",
                    sortAsc=False,
                )
                provider_call_count += 1
                page = list((response or {}).get("quotes") or [])
                for raw in page:
                    symbol = str((raw or {}).get("symbol") or "").upper().strip().replace(".", "-")
                    if symbol in requested:
                        classified[symbol] = {
                            "symbol": symbol,
                            "sector": PROJECT_SECTOR_MAP.get(sector, sector),
                            "provider_sector": sector,
                            "industry": None,
                            "provider": "yahoo-screener",
                            "source_url": "https://finance.yahoo.com/research-hub/screener/",
                            "source_status": "provider-classification",
                            "fetched_at": fetched_at,
                            "classification_version": SECTOR_CLASSIFICATION_VERSION,
                            "taxonomy_authoritative": False,
                            "caveat": "Yahoo screener sector-query membership mapped through project sector labels; raw provider sector is preserved and no official GICS, SIC, or index membership is claimed.",
                            "not_financial_advice": True,
                        }
                sources.append(
                    {
                        "provider": "yahoo-screener",
                        "source": f"Yahoo sector query: {sector}",
                        "source_url": "https://finance.yahoo.com/research-hub/screener/",
                        "source_status": "live/fresh",
                        "fetched_at": fetched_at,
                        "row_count": len(page),
                        "provider_call_count": 1,
                    }
                )
            except Exception as exc:
                sources.append(
                    {
                        "provider": "yahoo-screener",
                        "source": f"Yahoo sector query: {sector}",
                        "source_url": "https://finance.yahoo.com/research-hub/screener/",
                        "source_status": "unavailable",
                        "fetched_at": fetched_at,
                        "row_count": 0,
                        "provider_call_count": 1,
                        "data_gap": type(exc).__name__,
                    }
                )
        rows = [classified[symbol] for symbol in sorted(classified)]
        source_status = "live/fresh" if rows else "unavailable"
        summary = {
            "requested_count": len(requested),
            "classified_count": len(rows),
            "unclassified_count": len(requested) - len(rows),
            "provider_call_count": provider_call_count,
            "source_status": source_status,
            "taxonomy_authoritative": False,
            "industry_coverage_count": 0,
        }
        _SECTOR_CACHE[key] = {
            "stored_at": now,
            "rows": deepcopy(list(classified.values())),
            "sources": deepcopy(sources),
            "summary": deepcopy(summary),
        }
        return {
            "classification_version": SECTOR_CLASSIFICATION_VERSION,
            "rows": rows,
            "sources": sources,
            "summary": summary,
        }


def fetch_yahoo_batch_financial_snapshot(symbols: Iterable[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    requested = sorted({str(symbol or "").upper().strip().replace(".", "-") for symbol in symbols if str(symbol or "").strip()})
    fetched_at = _now_iso()
    if not requested:
        return [], {
            "provider": "yahoo-screener",
            "source_status": "unavailable",
            "fetched_at": fetched_at,
            "error": "No symbols supplied.",
            "row_count": 0,
        }
    snapshot, status = fetch_yahoo_us_market_snapshot(limit=250)
    requested_set = set(requested)
    rows = [
        {
            "symbol": row["symbol"],
            "market_cap": row.get("market_cap"),
            "trailing_pe": row.get("trailing_pe"),
            "forward_pe": row.get("forward_pe"),
            "price_to_book": row.get("price_to_book"),
            "eps_ttm": row.get("eps_ttm"),
            "eps_forward": row.get("eps_forward"),
            "dividend_yield": row.get("dividend_yield"),
            "financial_provider": row.get("financial_provider") or "yahoo-screener",
            "financial_source_url": row.get("financial_source_url"),
            "financial_fetched_at": row.get("financial_fetched_at") or status.get("fetched_at"),
            "financial_source_status": row.get("financial_source_status") or status.get("source_status"),
            "exchange_delay_minutes": row.get("exchange_delay_minutes"),
            "financial_caveat": row.get("financial_caveat"),
        }
        for row in snapshot
        if row["symbol"] in requested_set
    ]
    return rows, {
        **status,
        "row_count": len(rows),
        "requested_symbol_count": len(requested),
        "caveat": "One Yahoo screener batch is reused for broad observations and requested financial enrichment.",
        "data_gap": None if len(rows) == len(requested) else f"Financial snapshot covered {len(rows)}/{len(requested)} requested symbols.",
    }


def build_factor_catalog() -> list[dict[str, Any]]:
    return [
        _factor("return_1d_pct", "1D return", "close(t)/close(t-1)-1", 2, "high", "market history"),
        _factor("return_1m_pct", "1M return", "close(t)/close(t-22)-1", 23, "high", "market history"),
        _factor("realized_volatility_pct", "Realized volatility", "std(daily returns)*sqrt(252)", 21, "low", "market history"),
        _factor("drawdown_pct", "Drawdown", "close/running_max(close)-1", 2, "high", "market history"),
        _factor("rsi", "RSI(14)", "rolling mean gain/loss RSI", 15, "target55", "market history"),
        _factor("price_vs_sma20_pct", "Price vs SMA20", "close/SMA(20)-1", 20, "high", "market history"),
        _factor("market_cap", "Market capitalization", "provider value, static fallback kept separate", 1, "high", "financial snapshot"),
        _factor("trailing_pe", "Trailing P/E", "market price / trailing EPS", 1, "low", "financial snapshot"),
        _factor("forward_pe", "Forward P/E", "market price / provider forward EPS", 1, "low", "financial snapshot"),
        _factor("price_to_book", "Price to book", "market price / book value", 1, "low", "financial snapshot"),
        _factor("eps_ttm", "Trailing EPS", "provider trailing twelve-month EPS", 1, "positive", "financial snapshot"),
        _factor("data_quality_score", "Data completeness", "available required fields / declared fields", 1, "high", "project-native"),
    ]


def _factor(factor_id: str, label: str, formula: str, minimum: int, direction: str, provider_family: str) -> dict[str, Any]:
    return {
        "factor_id": factor_id,
        "label": label,
        "formula": formula,
        "minimum_observations": minimum,
        "direction": direction,
        "null_policy": "remain null; excluded when required by the selected rank model",
        "provider_family": provider_family,
        "not_financial_advice": True,
    }


def enrich_discovery_rows(
    rows: Iterable[dict[str, Any]],
    financial_rows: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    financial_by_symbol = {
        str(item.get("symbol") or "").upper(): dict(item)
        for item in financial_rows or []
        if str(item.get("symbol") or "").strip()
    }
    output: list[dict[str, Any]] = []
    for source_row in rows:
        row = deepcopy(dict(source_row))
        symbol = str(row.get("symbol") or "").upper()
        financial = financial_by_symbol.get(symbol, {})
        for field in _FINANCIAL_FIELDS:
            financial_value = _number(financial.get(field))
            if financial_value is not None:
                row[field] = financial_value
            elif field not in row:
                row[field] = None
        available_fields = sum(row.get(field) is not None for field in _TECHNICAL_FIELDS + _FINANCIAL_FIELDS)
        data_quality = round(available_fields / len(_TECHNICAL_FIELDS + _FINANCIAL_FIELDS) * 100, 2)
        factors = {
            **{field: _number(row.get(field)) for field in _TECHNICAL_FIELDS + _FINANCIAL_FIELDS},
            "valuation_available": any(row.get(field) is not None for field in ("trailing_pe", "forward_pe", "price_to_book")),
            "financial_coverage": sum(row.get(field) is not None for field in _FINANCIAL_FIELDS),
            "data_quality_score": data_quality,
            "trend_state": "above-sma20" if row.get("above_20dma") is True else "below-sma20" if row.get("above_20dma") is False else "unavailable",
        }
        row["factors"] = factors
        row["data_quality"] = {
            "score": data_quality,
            "status": "complete" if data_quality >= 80 else "partial",
            "available_field_count": available_fields,
            "declared_field_count": len(_TECHNICAL_FIELDS + _FINANCIAL_FIELDS),
            "missing_fields": [field for field in _TECHNICAL_FIELDS + _FINANCIAL_FIELDS if row.get(field) is None],
        }
        row["financial_snapshot"] = {
            "provider": financial.get("financial_provider") or "yahoo-screener",
            "source_url": financial.get("financial_source_url"),
            "fetched_at": financial.get("financial_fetched_at"),
            "source_status": financial.get("financial_source_status") or "unavailable",
            "exchange_delay_minutes": financial.get("exchange_delay_minutes"),
            "caveat": financial.get("financial_caveat") or "Batch financial fields unavailable for this bounded symbol.",
            "data_gap": None if financial else "No matching row in the batch financial snapshot.",
        }
        row["market_clock"] = {
            "market_data_as_of": row.get("market_data_as_of"),
            "retrieved_at": row.get("fetched_at"),
            "source_status": row.get("source_status"),
        }
        row["rank_models"] = {}
        output.append(row)

    rank_models = _apply_rank_models(output)
    return {
        "discovery_version": DISCOVERY_VERSION,
        "rows": output,
        "factor_catalog": build_factor_catalog(),
        "rank_models": rank_models,
    }


def _apply_rank_models(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for model_id, definition in RANK_MODEL_DEFINITIONS.items():
        eligible = []
        for row in rows:
            factors = row["factors"]
            missing = [factor for factor in definition["required_factors"] if factors.get(factor) is None]
            row["rank_models"][model_id] = {
                "model_id": model_id,
                "version": definition["version"],
                "eligible": not missing,
                "score": None,
                "rank": None,
                "contributions": [],
                "exclusion_reasons": missing,
            }
            if not missing:
                eligible.append(row)

        distributions = {
            factor: sorted(float(row["factors"][factor]) for row in eligible)
            for factor, _, direction in definition["components"]
            if direction not in {"target55", "positive"}
        }
        for row in eligible:
            contributions = []
            for factor, weight, direction in definition["components"]:
                raw = float(row["factors"][factor])
                component_score = _component_score(raw, distributions.get(factor, []), direction)
                contribution = round(component_score * weight * 100, 2)
                contributions.append(
                    {
                        "factor_id": factor,
                        "raw_value": raw,
                        "direction": direction,
                        "weight": weight,
                        "component_score": round(component_score * 100, 2),
                        "contribution": contribution,
                    }
                )
            score = round(sum(item["contribution"] for item in contributions), 2)
            row["rank_models"][model_id].update({"score": score, "contributions": contributions})

        ranked = sorted(eligible, key=lambda item: float(item["rank_models"][model_id]["score"]), reverse=True)
        for rank, row in enumerate(ranked, start=1):
            row["rank_models"][model_id]["rank"] = rank

        metadata[model_id] = {
            "model_id": model_id,
            "label": definition["label"],
            "version": definition["version"],
            "description": definition["description"],
            "required_factors": list(definition["required_factors"]),
            "formula": " + ".join(f"{weight:.0%} {factor}" for factor, weight, _ in definition["components"]),
            "eligible_count": len(eligible),
            "excluded_count": len(rows) - len(eligible),
            "null_policy": "Rows missing required factors are excluded.",
            "reconciliation_tolerance": 0.02,
            "not_financial_advice": True,
        }
    return metadata


def _component_score(value: float, distribution: list[float], direction: str) -> float:
    if direction == "target55":
        return max(0.0, min(1.0, 1.0 - abs(value - 55.0) / 45.0))
    if direction == "positive":
        return 1.0 if value > 0 else 0.0
    if not distribution:
        return 0.5
    if len(distribution) == 1:
        percentile = 1.0
    else:
        percentile = sum(item <= value for item in distribution) / len(distribution)
    return 1.0 - percentile if direction == "low" else percentile


def apply_discovery_filters(rows: Iterable[dict[str, Any]], filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    state = filters or {}
    sectors = {str(item) for item in state.get("sectors") or [] if str(item)}
    rank_model = str(state.get("rank") or "balanced")
    output = []
    for row in rows:
        factors = row.get("factors") or {}
        if sectors and str(row.get("sector")) not in sectors:
            continue
        if not _bucket_match(_number(row.get("market_cap")), str(state.get("market_cap") or "all"), "market_cap"):
            continue
        if not _bucket_match(_number(row.get("return_1d_pct")), str(state.get("return_1d") or "all"), "return"):
            continue
        if not _bucket_match(_number(row.get("return_1m_pct")), str(state.get("return_1m") or "all"), "return"):
            continue
        if not _bucket_match(_number(row.get("realized_volatility_pct")), str(state.get("volatility") or "all"), "volatility"):
            continue
        if not _bucket_match(_number(row.get("rsi")), str(state.get("rsi") or "all"), "rsi"):
            continue
        trend = str(state.get("trend") or "all")
        if trend != "all" and factors.get("trend_state") != trend:
            continue
        valuation = str(state.get("valuation") or "all")
        if valuation == "available" and factors.get("valuation_available") is not True:
            continue
        if valuation == "missing" and factors.get("valuation_available") is True:
            continue
        quality = str(state.get("quality") or "all")
        if quality != "all" and str((row.get("data_quality") or {}).get("status")) != quality:
            continue
        if rank_model in RANK_MODEL_DEFINITIONS and not (row.get("rank_models") or {}).get(rank_model, {}).get("eligible"):
            continue
        output.append(row)
    return sorted(
        output,
        key=lambda item: float(((item.get("rank_models") or {}).get(rank_model) or {}).get("score") or -1),
        reverse=True,
    )


def _bucket_match(value: float | None, bucket: str, family: str) -> bool:
    if bucket == "all":
        return True
    if value is None:
        return False
    if family == "market_cap":
        return (
            (bucket == "mega" and value >= 200_000_000_000)
            or (bucket == "large" and 10_000_000_000 <= value < 200_000_000_000)
            or (bucket == "mid" and 2_000_000_000 <= value < 10_000_000_000)
        )
    if family == "return":
        return (
            (bucket == "positive" and value > 0)
            or (bucket == "negative" and value < 0)
            or (bucket == "above2" and value >= 2)
            or (bucket == "below-2" and value <= -2)
        )
    if family == "volatility":
        return (
            (bucket == "low" and value < 20)
            or (bucket == "moderate" and 20 <= value <= 35)
            or (bucket == "high" and value > 35)
        )
    if family == "rsi":
        return (
            (bucket == "oversold" and value < 30)
            or (bucket == "neutral" and 30 <= value <= 70)
            or (bucket == "overbought" and value > 70)
            or (bucket == "constructive" and 50 <= value <= 70)
        )
    return False


def discovery_filter_options(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return {
        "universe": ["bounded-us-largecap"],
        "sectors": sorted({str(row.get("sector")) for row in rows if row.get("sector")}),
        "market_cap": ["all", "mega", "large", "mid"],
        "return_1d": ["all", "positive", "negative", "above2", "below-2"],
        "return_1m": ["all", "positive", "negative", "above2", "below-2"],
        "volatility": ["all", "low", "moderate", "high"],
        "rsi": ["all", "oversold", "neutral", "constructive", "overbought"],
        "trend": ["all", "above-sma20", "below-sma20"],
        "valuation": ["all", "available", "missing"],
        "quality": ["all", "complete", "partial"],
        "rank": list(RANK_MODEL_DEFINITIONS),
        "display": ["heatmap", "table", "scatter", "factors"],
    }
