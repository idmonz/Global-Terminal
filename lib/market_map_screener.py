from __future__ import annotations

import math
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from .market_discovery import (
    DISCOVERY_VERSION,
    RANK_MODEL_DEFINITIONS,
    discovery_filter_options,
    enrich_discovery_rows,
    fetch_yahoo_batch_financial_snapshot,
    fetch_yahoo_sector_classification,
    fetch_yahoo_us_market_snapshot,
)
from .market_identity import (
    build_market_identity_contract,
    fetch_sec_ticker_exchange_directory,
)
from .market_intelligence import build_market_intelligence_contract
from .market_universe import fetch_nasdaq_symbol_directory
from .screeners import build_stock_screener
from .symbol_workstation import build_symbol_directory_contract


MARKET_MAP_SCREENER_VERSION = "market_map_screener.v2"
_CACHE_TTL_SECONDS = 600
_CACHE_STALE_SECONDS = 3600
_CACHE_LOCK = threading.Lock()
_RUNTIME_CACHE: dict[str, dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _source_status(status: dict[str, Any]) -> str:
    raw = str(status.get("source_status") or status.get("status") or "unknown").lower()
    if raw in {"fresh", "live", "live/fresh", "ok", "available"}:
        return "live/fresh"
    if raw == "stale":
        return "stale"
    if raw == "cached" or status.get("cached") is True:
        return "cached"
    if raw in {"fixture", "static/proxy", "provider-observed"}:
        return raw
    return "unavailable"


def _rank_rows(rows: list[dict[str, Any]]) -> None:
    eligible = [
        row
        for row in rows
        if row.get("return_1m_pct") is not None and row.get("realized_volatility_pct") is not None
    ]
    if not eligible:
        for row in rows:
            row["rank_eligible"] = False
            row["rank_score"] = None
            row["rank"] = None
        return

    returns = sorted(float(row["return_1m_pct"]) for row in eligible)
    volatility = sorted(float(row["realized_volatility_pct"]) for row in eligible)
    drawdowns = sorted(float(row.get("drawdown_pct") or 0.0) for row in eligible)

    def percentile(values: list[float], value: float) -> float:
        if len(values) == 1:
            return 1.0
        return sum(item <= value for item in values) / len(values)

    for row in rows:
        monthly = row.get("return_1m_pct")
        vol = row.get("realized_volatility_pct")
        if monthly is None or vol is None:
            row["rank_eligible"] = False
            row["rank_score"] = None
            row["rank"] = None
            continue
        return_score = percentile(returns, float(monthly))
        low_vol_score = 1.0 - percentile(volatility, float(vol))
        drawdown_score = percentile(drawdowns, float(row.get("drawdown_pct") or 0.0))
        row["rank_eligible"] = True
        row["rank_score"] = round((return_score * 0.55 + low_vol_score * 0.30 + drawdown_score * 0.15) * 100, 2)

    for index, row in enumerate(
        sorted((item for item in rows if item["rank_eligible"]), key=lambda item: float(item["rank_score"]), reverse=True),
        start=1,
    ):
        row["rank"] = index


def _normalize_runtime_rows(frame: Any, status: dict[str, Any]) -> list[dict[str, Any]]:
    records = frame.to_dict(orient="records") if hasattr(frame, "to_dict") else list(frame or [])
    fetched_at = status.get("fetched_at") or _now_iso()
    source_status = _source_status(status)
    rows: list[dict[str, Any]] = []
    for item in records:
        symbol = str(item.get("ticker") or item.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        price = _clean_number(item.get("price"))
        data_gap = None if price is not None else "Provider returned no usable price history for this symbol."
        rows.append(
            {
                "symbol": symbol,
                "name": item.get("company") or item.get("name") or symbol,
                "asset_class": "equity",
                "sector": item.get("sector") or "Unclassified",
                "industry": item.get("industry") or "Unclassified",
                "region": "United States",
                "exchange": item.get("exchange") or "US listed",
                "market_cap": _clean_number(item.get("market_cap")),
                "size_value": _clean_number(item.get("market_cap")) or 1.0,
                "size_metric": "market_cap",
                "price": price,
                "return_1d_pct": _clean_number(item.get("return_1d_pct")),
                "return_1w_pct": _clean_number(item.get("return_1w_pct")),
                "return_1m_pct": _clean_number(item.get("return_1m_pct")),
                "return_ytd_pct": _clean_number(item.get("return_ytd_pct")),
                "realized_volatility_pct": _clean_number(item.get("realized_volatility_pct")),
                "drawdown_pct": _clean_number(item.get("drawdown_pct")),
                "rsi": _clean_number(item.get("rsi")),
                "price_vs_sma20_pct": _clean_number(item.get("price_vs_sma20_pct")),
                "above_20dma": item.get("above_20dma"),
                "volume_zscore": _clean_number(item.get("volume_zscore")),
                "range_52w_position": _clean_number(item.get("range_52w_position")),
                "market_data_as_of": item.get("market_data_as_of"),
                "provider": status.get("provider") or "yfinance",
                "source_url": f"https://finance.yahoo.com/quote/{quote(symbol)}",
                "fetched_at": fetched_at,
                "freshness": source_status,
                "source_status": source_status,
                "confidence": 0.9 if price is not None else 0.2,
                "taxonomy_source_status": "static/proxy",
                "coordinate_method": "not_applicable",
                "caveat": "Delayed public market history; taxonomy comes from the local reviewed constituent registry.",
                "data_gap": data_gap,
                "not_financial_advice": True,
            }
        )
    _rank_rows(rows)
    return rows


def _fixture_rows() -> list[dict[str, Any]]:
    market = build_market_intelligence_contract(include_runtime=False)
    rows: list[dict[str, Any]] = []
    for item in market.get("market_heatmap") or []:
        symbol = str(item.get("symbol") or "").strip().upper()
        daily = _clean_number(item.get("daily_return_pct")) or 0.0
        weight = _clean_number(item.get("market_cap_weight")) or 1.0
        rows.append(
            {
                "symbol": symbol,
                "name": item.get("label") or symbol,
                "asset_class": "equity",
                "sector": item.get("sector") or "Unclassified",
                "industry": item.get("industry") or "Unclassified",
                "region": "Fixture",
                "exchange": "Fixture",
                "market_cap": None,
                "size_value": weight,
                "size_metric": "fixture_relative_weight",
                "price": None,
                "return_1d_pct": daily,
                "return_1w_pct": round(daily * 1.8, 4),
                "return_1m_pct": round(daily * 3.0, 4),
                "return_ytd_pct": None,
                "realized_volatility_pct": round(18.0 + abs(daily) * 2.0, 4),
                "drawdown_pct": round(-abs(daily) * 1.5, 4),
                "rsi": None,
                "price_vs_sma20_pct": round(daily * 1.4, 4),
                "above_20dma": daily >= 0,
                "volume_zscore": None,
                "range_52w_position": None,
                "market_data_as_of": "2026-06-15T20:00:00+00:00",
                "provider": "phase5i.fixture",
                "source_url": f"https://example.test/phase-5i/market-map/{quote(symbol)}",
                "fetched_at": "2026-06-16T00:00:00+00:00",
                "freshness": "fixture",
                "source_status": "fixture",
                "confidence": 0.25,
                "taxonomy_source_status": "fixture",
                "coordinate_method": "not_applicable",
                "caveat": "Deterministic synthetic fixture metrics for product and regression testing only.",
                "data_gap": "Use live-if-available mode for provider-backed returns and volatility.",
                "not_financial_advice": True,
            }
        )
    _rank_rows(rows)
    return rows


def _fixture_financial_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for index, row in enumerate(rows):
        symbol = str(row.get("symbol") or "")
        market_cap = 25_000_000_000 + (len(rows) - index) * 8_500_000_000
        output.append(
            {
                "symbol": symbol,
                "market_cap": market_cap,
                "trailing_pe": round(13.0 + (index % 12) * 1.35, 2),
                "forward_pe": round(12.0 + (index % 10) * 1.2, 2),
                "price_to_book": round(1.4 + (index % 8) * 0.55, 2),
                "eps_ttm": round(1.0 + (index % 9) * 0.8, 2),
                "eps_forward": round(1.2 + (index % 9) * 0.85, 2),
                "financial_provider": "phase5o.fixture",
                "financial_source_url": f"https://example.test/phase-5o/financial/{quote(symbol)}",
                "financial_fetched_at": "2026-06-16T00:00:00+00:00",
                "financial_source_status": "fixture",
                "exchange_delay_minutes": None,
                "financial_caveat": "Deterministic synthetic financial fields for product and regression testing only.",
            }
        )
    return output


def _fixture_universe_contract(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": "market_universe.v1",
        "scope": "deterministic-product-fixture",
        "scope_label": "Fixture regression universe",
        "observation_provider": "phase5i.fixture",
        "observation_source_status": "fixture",
        "screened_observation_count": len(rows),
        "observation_count": len(rows),
        "excluded_unverified_observation_count": 0,
        "listing_provider": "fixture",
        "listing_source_status": "fixture",
        "official_listing_coverage_count": 0,
        "official_listing_directory_count": 0,
        "listing_as_of": "2026-06-16T00:00:00+00:00",
        "taxonomy_provider": "phase5i.fixture",
        "taxonomy_source_status": "fixture",
        "taxonomy_coverage_count": len(rows),
        "unclassified_count": 0,
        "authoritative_listing_identity": False,
        "authoritative_index_membership": False,
        "taxonomy_authoritative": False,
        "caveat": "Synthetic rows support deterministic UI and regression testing only.",
        "data_gap": "Use live-if-available mode for delayed provider observations and official listing identity.",
    }


def _workstation_symbols() -> set[str]:
    all_rows = build_symbol_directory_contract().get("identities") or []
    return {str(row.get("symbol") or "").upper() for row in all_rows}


def _official_workstation_supported(identity: dict[str, Any] | None) -> bool:
    if not identity:
        return False
    return (
        str(identity.get("listing_status") or "").lower() in {"active", "listed"}
        and str(identity.get("security_type") or "").lower()
        in {"equity", "etf", "common-stock", "common stock"}
        and bool(identity.get("ticker") or identity.get("symbol"))
    )


def _merge_broad_runtime_rows(
    history_rows: list[dict[str, Any]],
    broad_rows: list[dict[str, Any]],
    identity_contract: dict[str, Any],
    classification_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    history_lookup = {str(row.get("symbol") or "").upper(): deepcopy(row) for row in history_rows}
    identity_lookup = {
        str(row.get("symbol") or "").upper(): row
        for row in identity_contract.get("rows") or []
    }
    classification_lookup = {
        str(row.get("symbol") or "").upper(): row
        for row in classification_contract.get("rows") or []
    }
    workstation_symbols = _workstation_symbols()
    output: list[dict[str, Any]] = []
    for observation in broad_rows:
        symbol = str(observation.get("symbol") or "").upper()
        if not symbol:
            continue
        history = history_lookup.get(symbol)
        identity = identity_lookup.get(symbol)
        if identity is None:
            continue
        classification = classification_lookup.get(symbol)
        local_taxonomy = history is not None and str(history.get("sector") or "Unclassified") != "Unclassified"
        membership = {
            "provider": identity.get("listing_provider"),
            "source_url": identity.get("listing_source_url"),
            "source_status": identity.get("listing_source_status"),
            "as_of": identity.get("listing_as_of"),
            "listing_status": identity.get("listing_status"),
            "exchange": identity.get("exchange"),
            "mic": identity.get("mic"),
            "security_type": identity.get("security_type"),
            "cik": identity.get("cik"),
            "sec_source_status": identity.get("sec_source_status"),
            "identity_conflict": identity.get("identity_conflict"),
            "caveat": identity.get("caveat"),
        }
        if local_taxonomy:
            classification_conflict = bool(
                classification
                and classification.get("sector")
                and str(classification.get("sector")) != str(history.get("sector"))
            )
            taxonomy = {
                "provider": "phase5i.local_taxonomy",
                "source": "static/index_constituents/sp500.csv",
                "source_status": "static/proxy",
                "classification_version": "phase5i.local_taxonomy.v1",
                "reviewed_at": "2026-06-16T00:00:00+00:00",
                "sector": history.get("sector"),
                "industry": history.get("industry"),
                "taxonomy_authoritative": False,
                "provider_sector": (classification or {}).get("provider_sector"),
                "classification_conflict": classification_conflict,
                "caveat": "Reviewed local sector/industry reference; not current index membership or official GICS.",
            }
        elif classification:
            taxonomy = {
                **classification,
                "source": "Yahoo sector-query membership",
                "industry": None,
                "reviewed_at": classification.get("fetched_at"),
            }
        else:
            taxonomy = {
                "provider": "unavailable",
                "source": None,
                "source_status": "unavailable",
                "classification_version": "market_taxonomy.v2",
                "reviewed_at": None,
                "sector": None,
                "industry": None,
                "taxonomy_authoritative": False,
                "caveat": "No reviewed local or provider sector classification is attached to this observation.",
            }
        row = deepcopy(history) if history else {
            "symbol": symbol,
            "name": observation.get("name") or symbol,
            "asset_class": observation.get("asset_class") or "equity",
            "sector": "Unclassified",
            "industry": "Unclassified",
            "region": "United States",
            "return_1w_pct": None,
            "return_1m_pct": None,
            "return_ytd_pct": None,
            "realized_volatility_pct": None,
            "drawdown_pct": None,
            "rsi": None,
            "price_vs_sma20_pct": None,
            "above_20dma": None,
            "volume_zscore": None,
            "range_52w_position": None,
            "coordinate_method": "not_applicable",
        }
        market_cap = _clean_number(observation.get("market_cap"))
        price = _clean_number(observation.get("price"))
        row.update(
            {
                "name": observation.get("name") or row.get("name") or symbol,
                "sector": taxonomy.get("sector") or row.get("sector") or "Unclassified",
                "industry": taxonomy.get("industry") or row.get("industry") or "Unclassified",
                "exchange": membership.get("exchange") or observation.get("exchange") or row.get("exchange"),
                "mic": membership.get("mic"),
                "country": "United States",
                "market_cap": market_cap if market_cap is not None else row.get("market_cap"),
                "size_value": market_cap if market_cap is not None else _clean_number(observation.get("volume")) or 1.0,
                "size_metric": "market_cap" if market_cap is not None else "regular_market_volume",
                "price": price if price is not None else row.get("price"),
                "return_1d_pct": _clean_number(observation.get("return_1d_pct")),
                "volume": _clean_number(observation.get("volume")),
                "average_volume_3m": _clean_number(observation.get("average_volume_3m")),
                "relative_volume": _clean_number(observation.get("relative_volume")),
                "market_data_as_of": observation.get("market_data_as_of") or row.get("market_data_as_of"),
                "provider": observation.get("provider") or "yahoo-screener",
                "source_url": observation.get("source_url"),
                "fetched_at": observation.get("fetched_at") or row.get("fetched_at") or _now_iso(),
                "freshness": observation.get("source_status") or "unknown",
                "source_status": observation.get("source_status") or "unknown",
                "history_source_status": history.get("source_status") if history else "unavailable",
                "confidence": 0.92 if price is not None else 0.25,
                "taxonomy_source_status": taxonomy["source_status"],
                "membership": membership,
                "taxonomy": taxonomy,
                "workstation_supported": (
                    symbol in workstation_symbols
                    or _official_workstation_supported(identity)
                ),
                "caveat": (
                    f"Delayed public market observation. {history.get('caveat') or ''} "
                    "Listing identity and sector taxonomy have independent source states."
                ).strip()
                if history
                else "Delayed public market observation. Listing identity and sector taxonomy have independent source states.",
                "data_gap": (
                    history.get("data_gap")
                    if history
                    else "Historical momentum, volatility and drawdown factors are unavailable for this broad-only observation."
                ),
                "not_financial_advice": True,
            }
        )
        output.append(row)
    seen = {row["symbol"] for row in output}
    for row in history_rows:
        symbol = str(row.get("symbol") or "").upper()
        if symbol in seen:
            continue
        identity = identity_lookup.get(symbol)
        fallback = deepcopy(row)
        fallback["membership"] = (
            {
                "provider": identity.get("listing_provider"),
                "source_url": identity.get("listing_source_url"),
                "source_status": identity.get("listing_source_status"),
                "as_of": identity.get("listing_as_of"),
                "listing_status": identity.get("listing_status"),
                "exchange": identity.get("exchange"),
                "mic": identity.get("mic"),
                "security_type": identity.get("security_type"),
                "cik": identity.get("cik"),
                "sec_source_status": identity.get("sec_source_status"),
                "caveat": identity.get("caveat"),
            }
            if identity
            else {
                "provider": "unavailable",
                "source_url": None,
                "source_status": "unavailable",
                "as_of": None,
                "listing_status": "unverified",
                "exchange": fallback.get("exchange"),
                "mic": None,
                "security_type": fallback.get("asset_class") or "equity",
                "caveat": "The history row was not present in the current official listing-directory match.",
            }
        )
        fallback["country"] = "United States"
        fallback["mic"] = identity.get("mic") if identity else None
        fallback["taxonomy"] = {
            "provider": "phase5i.local_taxonomy",
            "source": "static/index_constituents/sp500.csv",
            "source_status": "static/proxy",
            "reviewed_at": "2026-06-16T00:00:00+00:00",
            "sector": fallback.get("sector"),
            "industry": fallback.get("industry"),
            "caveat": "Reviewed local sector/industry reference; not current index membership.",
        }
        fallback["workstation_supported"] = (
            symbol in workstation_symbols
            or _official_workstation_supported(identity)
        )
        output.append(fallback)
    _rank_rows(output)
    return output


def _financial_rows_from_broad_snapshot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "market_cap",
        "trailing_pe",
        "forward_pe",
        "price_to_book",
        "eps_ttm",
        "eps_forward",
        "dividend_yield",
        "financial_provider",
        "financial_source_url",
        "financial_fetched_at",
        "financial_source_status",
        "exchange_delay_minutes",
        "financial_caveat",
    )
    return [
        {"symbol": row["symbol"], **{field: row.get(field) for field in fields}}
        for row in rows
        if row.get("symbol")
    ]


def _runtime_rows(period: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cache_key = f"{period}:{id(build_stock_screener)}"
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _RUNTIME_CACHE.get(cache_key)
        if cached and now - cached["stored_at"] <= _CACHE_TTL_SECONDS:
            rows = deepcopy(cached["rows"])
            for row in rows:
                row["freshness"] = "cached"
                row["source_status"] = "cached"
                row["caveat"] = f"{row['caveat']} Served from the {int(_CACHE_TTL_SECONDS / 60)} minute runtime cache."
            return rows, {**cached["status"], "status": "cached", "cached": True}

        try:
            frame, result = build_stock_screener(period=period)
            status = result.to_dict() if hasattr(result, "to_dict") else dict(result or {})
            rows = _normalize_runtime_rows(frame, status)
            if rows and any(row.get("price") is not None for row in rows):
                _RUNTIME_CACHE[cache_key] = {"stored_at": now, "rows": deepcopy(rows), "status": deepcopy(status)}
                return rows, status
            raise RuntimeError(status.get("error") or "Provider returned no usable screener rows")
        except Exception as exc:
            if cached and now - cached["stored_at"] <= _CACHE_STALE_SECONDS:
                rows = deepcopy(cached["rows"])
                for row in rows:
                    row["freshness"] = "stale"
                    row["source_status"] = "stale"
                    row["caveat"] = f"{row['caveat']} Live refresh failed; stale cache retained."
                    row["data_gap"] = str(exc)
                return rows, {**cached["status"], "status": "stale", "cached": True, "warning": str(exc)}
            return [], {
                "provider": "yfinance",
                "source": "stock screener",
                "status": "unavailable",
                "fetched_at": _now_iso(),
                "cached": False,
                "error": str(exc),
            }


def _sector_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    sectors = sorted({str(row.get("sector") or "Unclassified") for row in rows})
    total_size = sum(float(row.get("size_value") or 0.0) for row in rows) or 1.0
    for sector in sectors:
        members = [row for row in rows if str(row.get("sector") or "Unclassified") == sector]
        returns = [float(row["return_1d_pct"]) for row in members if row.get("return_1d_pct") is not None]
        output.append(
            {
                "sector": sector,
                "instrument_count": len(members),
                "size_share_pct": round(sum(float(row.get("size_value") or 0.0) for row in members) / total_size * 100, 4),
                "median_return_1d_pct": round(sorted(returns)[len(returns) // 2], 4) if returns else None,
                "advance_count": sum(value > 0 for value in returns),
                "decline_count": sum(value < 0 for value in returns),
                "source_status": _aggregate_status(members),
                "not_financial_advice": True,
            }
        )
    return output


def _aggregate_status(rows: list[dict[str, Any]]) -> str:
    statuses = {str(row.get("source_status") or "unknown") for row in rows}
    for candidate in ("live/fresh", "cached", "stale", "fixture", "unavailable"):
        if candidate in statuses:
            return candidate
    return "unknown"


def build_market_map_screener_contract(
    *,
    include_runtime: bool = False,
    period: str = "3mo",
) -> dict[str, Any]:
    if include_runtime:
        history_rows, runtime_status = _runtime_rows(period)
        broad_rows, broad_status = fetch_yahoo_us_market_snapshot(limit=750, page_size=250)
        listing_contract = fetch_nasdaq_symbol_directory()
        sec_contract = fetch_sec_ticker_exchange_directory()
        identity_contract = build_market_identity_contract(
            listing_contract=listing_contract,
            sec_rows=sec_contract.get("rows") or [],
            sec_source=sec_contract.get("source"),
        )
        identity_symbols = {str(row.get("symbol") or "").upper() for row in identity_contract.get("rows") or []}
        classification_contract = fetch_yahoo_sector_classification(
            str(row.get("symbol") or "").upper()
            for row in broad_rows
            if str(row.get("symbol") or "").upper() in identity_symbols
        )
        official_broad_count = sum(
            str(row.get("symbol") or "").upper() in identity_symbols
            for row in broad_rows
        )
        rows = (
            _merge_broad_runtime_rows(history_rows, broad_rows, identity_contract, classification_contract)
            if broad_rows
            else history_rows
        )
        listing_summary = listing_contract.get("summary") or {}
        official_listing_coverage = sum(
            str((row.get("membership") or {}).get("source_status")) == "official/current-day"
            for row in rows
        )
        taxonomy_coverage = sum(
            str((row.get("taxonomy") or {}).get("source_status"))
            in {"static/proxy", "provider-classification", "cached/provider-classification"}
            for row in rows
        )
        local_taxonomy_coverage = sum(
            str((row.get("taxonomy") or {}).get("source_status")) == "static/proxy"
            for row in rows
        )
        provider_taxonomy_coverage = taxonomy_coverage - local_taxonomy_coverage
        industry_coverage = sum(
            str(row.get("industry") or "Unclassified") != "Unclassified"
            for row in rows
        )
        taxonomy_conflicts = sum(
            bool((row.get("taxonomy") or {}).get("classification_conflict"))
            for row in rows
        )
        universe_contract = {
            "version": "market_universe.v2",
            "identity_version": identity_contract.get("identity_version"),
            "classification_version": classification_contract.get("classification_version"),
            "scope": "top-us-equity-screener-observations",
            "scope_label": "Top US public screener observations by market capitalization",
            "observation_provider": broad_status.get("provider") or "yahoo-screener",
            "observation_source_status": _source_status(broad_status),
            "screened_observation_count": len(broad_rows),
            "observation_count": official_broad_count,
            "excluded_unverified_observation_count": len(broad_rows) - official_broad_count,
            "listing_provider": "nasdaq_trader",
            "listing_source_status": listing_summary.get("source_status") or "unavailable",
            "official_listing_coverage_count": official_listing_coverage,
            "official_listing_directory_count": listing_summary.get("listing_count") or 0,
            "listing_as_of": listing_summary.get("directory_as_of"),
            "taxonomy_provider": "mixed:local-reviewed+yahoo-provider-classification",
            "taxonomy_source_status": "mixed/proxy" if taxonomy_coverage else "unavailable",
            "taxonomy_coverage_count": taxonomy_coverage,
            "local_taxonomy_coverage_count": local_taxonomy_coverage,
            "provider_taxonomy_coverage_count": provider_taxonomy_coverage,
            "industry_coverage_count": industry_coverage,
            "taxonomy_conflict_count": taxonomy_conflicts,
            "unclassified_count": len(rows) - taxonomy_coverage,
            "authoritative_listing_identity": bool(listing_summary.get("authoritative_listing_identity")),
            "authoritative_index_membership": False,
            "taxonomy_authoritative": False,
            "caveat": "Official listing identity, SEC CIK identity, delayed observations, reviewed local taxonomy, and Yahoo provider sector classification remain independent evidence layers.",
            "data_gap": "No authoritative index membership or complete official GICS/industry security master is attached.",
        }
    else:
        rows = _fixture_rows()
        runtime_status = {
            "provider": "phase5i.fixture",
            "source": "deterministic market map fixture",
            "status": "fixture",
            "fetched_at": "2026-06-16T00:00:00+00:00",
            "cached": False,
            "error": None,
        }
        broad_status = runtime_status
        listing_contract = {"rows": [], "sources": [], "summary": {"source_status": "fixture", "listing_count": 0}}
        identity_contract = {"rows": [], "sources": [], "summary": {}}
        classification_contract = {"rows": [], "sources": [], "summary": {}}
        universe_contract = _fixture_universe_contract(rows)
        workstation_symbols = _workstation_symbols()
        for row in rows:
            row["membership"] = {
                "provider": "phase5i.fixture",
                "source_url": row.get("source_url"),
                "source_status": "fixture",
                "as_of": row.get("fetched_at"),
                "listing_status": "fixture",
                "exchange": "Fixture",
                "mic": None,
                "security_type": "equity",
                "caveat": "Synthetic fixture identity; no listing claim.",
            }
            row["taxonomy"] = {
                "provider": "phase5i.fixture",
                "source": "deterministic fixture",
                "source_status": "fixture",
                "reviewed_at": row.get("fetched_at"),
                "sector": row.get("sector"),
                "industry": row.get("industry"),
                "caveat": "Synthetic fixture taxonomy.",
            }
            row["country"] = "Fixture"
            row["mic"] = None
            row["workstation_supported"] = row.get("symbol") in workstation_symbols
    if include_runtime and rows and broad_rows:
        financial_rows = _financial_rows_from_broad_snapshot(broad_rows)
        financial_status = {
            **broad_status,
            "row_count": len(financial_rows),
            "requested_symbol_count": len(rows),
            "provider_call_count": 0,
            "caveat": "Financial fields are reused from the same bounded Yahoo screener pages; no additional provider call is made.",
            "data_gap": None if financial_rows else "No broad financial fields were available.",
        }
    elif include_runtime and rows:
        financial_rows, financial_status = fetch_yahoo_batch_financial_snapshot(row["symbol"] for row in rows)
    elif rows:
        financial_rows = _fixture_financial_rows(rows)
        financial_status = {
            "provider": "phase5o.fixture",
            "source": "deterministic financial discovery fixture",
            "source_url": "https://example.test/phase-5o/financial",
            "source_status": "fixture",
            "freshness": "fixture",
            "fetched_at": "2026-06-16T00:00:00+00:00",
            "row_count": len(financial_rows),
            "requested_symbol_count": len(rows),
            "cached": False,
            "error": None,
            "caveat": "Synthetic financial values support deterministic rank and UI regression tests only.",
            "data_gap": "Use live-if-available mode for public provider-backed financial fields.",
        }
    else:
        financial_rows = []
        financial_status = {
            "provider": "yahoo-screener",
            "source": "Yahoo Finance public equity screener",
            "source_status": "unavailable",
            "freshness": "unavailable",
            "fetched_at": _now_iso(),
            "row_count": 0,
            "requested_symbol_count": 0,
            "cached": False,
            "error": "No bounded market-history rows were available.",
            "caveat": "Financial discovery is skipped when the bounded technical universe is empty.",
            "data_gap": "No symbols were available for batch financial enrichment.",
        }
    discovery = enrich_discovery_rows(rows, financial_rows)
    rows = discovery["rows"]
    ranked = sorted(
        (row for row in rows if row.get("rank_eligible") is True),
        key=lambda row: int(row.get("rank") or 10**9),
    )
    scatter = [
        {
            "symbol": row["symbol"],
            "name": row["name"],
            "sector": row["sector"],
            "return_1m_pct": row["return_1m_pct"],
            "realized_volatility_pct": row["realized_volatility_pct"],
            "rank_score": row["rank_score"],
            "source_status": row["source_status"],
        }
        for row in ranked
    ]
    sectors = _sector_summaries(rows)
    source_status = _source_status(broad_status if include_runtime else runtime_status)
    listing_sources = list(listing_contract.get("sources") or [])
    identity_sources = list(identity_contract.get("sources") or [])
    classification_sources = list(classification_contract.get("sources") or [])
    unavailable = [] if rows else [{
        "provider": runtime_status.get("provider") or "yfinance",
        "source_status": "unavailable",
        "availability": "unavailable",
        "error": runtime_status.get("error") or "No screener rows available.",
        "recommended_action": "Retry later or use deterministic fixture mode.",
        "not_financial_advice": True,
    }]
    if include_runtime and str((listing_contract.get("summary") or {}).get("source_status")) == "unavailable":
        unavailable.append(
            {
                "provider": "nasdaq_trader",
                "source_status": "unavailable",
                "availability": "unavailable",
                "error": "Official listing directory was unavailable; market observations remain provider-observed.",
                "recommended_action": "Retry after the Nasdaq Trader directory is reachable.",
                "not_financial_advice": True,
            }
        )
    saved_screen_readiness = {
        "store_status": "local-api-required",
        "privacy_scope": "local-private",
        "schema_version": "saved_market_screen.v1",
        "cloud_sync": "unavailable",
        "hosted_auth": "unavailable",
        "url_private_content_allowed": False,
        "release_private_content_allowed": False,
    }
    return {
        "market_map_screener_version": MARKET_MAP_SCREENER_VERSION,
        "discovery_version": DISCOVERY_VERSION,
        "workspace": "market-map-screener",
        "instruments": rows,
        "heatmap_tiles": rows,
        "ranked_rows": ranked,
        "scatter_points": scatter,
        "sector_summaries": sectors,
        "factor_catalog": discovery["factor_catalog"],
        "rank_models": discovery["rank_models"],
        "universe_contract": universe_contract,
        "saved_screen_readiness": saved_screen_readiness,
        "filter_options": {
            "asset_classes": sorted({str(row.get("asset_class")) for row in rows if row.get("asset_class")}),
            "sectors": [row["sector"] for row in sectors],
            "industries": sorted({str(row.get("industry")) for row in rows if row.get("industry")}),
            "countries": sorted({str(row.get("country") or row.get("region")) for row in rows if row.get("country") or row.get("region")}),
            "exchanges": sorted({str(row.get("exchange")) for row in rows if row.get("exchange")}),
            "regions": sorted({str(row.get("region")) for row in rows if row.get("region")}),
            "source_statuses": sorted({str(row.get("source_status")) for row in rows if row.get("source_status")}),
            "sort_metrics": ["rank_score", "market_cap", "return_1d_pct", "return_1m_pct", "realized_volatility_pct", "drawdown_pct"],
            "size_metrics": ["market_cap", "volume", "equal"],
            "color_metrics": ["return_1d_pct", "return_1m_pct", "relative_volume"],
            "grouping": ["sector", "industry", "none"],
            "eligibility": ["all", "eligible", "ineligible"],
            "discovery": discovery_filter_options(rows),
        },
        "source_register": [
            {
                **runtime_status,
                "source_status": source_status,
                "row_count": len(rows),
                "caveat": "Yahoo Finance supplies delayed public history; index taxonomy is local static/proxy metadata.",
                "data_gap": runtime_status.get("error"),
                "not_financial_advice": True,
            },
            {
                **broad_status,
                "source_status": _source_status(broad_status),
                "row_count": universe_contract["screened_observation_count"],
                "not_financial_advice": True,
            },
            {
                **financial_status,
                "row_count": len(financial_rows),
                "not_financial_advice": True,
            },
            *listing_sources,
            *[
                source
                for source in identity_sources
                if source not in listing_sources
            ],
            *classification_sources,
            {
                "provider": "phase5i.local_taxonomy",
                "source": "static/index_constituents/sp500.csv",
                "source_status": "static/proxy" if include_runtime else "fixture",
                "row_count": universe_contract["taxonomy_coverage_count"],
                "fetched_at": "2026-06-16T00:00:00+00:00" if include_runtime else "2026-06-16T00:00:00+00:00",
                "caveat": "Local reviewed sector/industry reference; current index membership is not claimed.",
                "data_gap": "Provider sector classification is not official GICS; broad industry coverage remains incomplete.",
                "not_financial_advice": True,
            },
        ],
        "unavailable_sources": unavailable,
        "readiness": {
            "live_universe_claimed": bool(rows and source_status in {"live/fresh", "cached", "stale"}),
            "authoritative_listing_identity_claimed": bool(universe_contract["authoritative_listing_identity"]),
            "authoritative_index_membership_claimed": False,
            "authoritative_taxonomy_claimed": False,
            "universe_scope": universe_contract["scope"],
            "history_window": period,
            "ranking_method": "Four explicit, versioned rank models with per-factor contribution reconciliation.",
            "default_rank_model": "balanced",
            "rank_model_ids": list(RANK_MODEL_DEFINITIONS),
            "rank_missing_values_as_zero": False,
            "saved_screen_store": saved_screen_readiness,
            "heatmap_size_metric": "selectable: market_cap, volume, equal",
            "heatmap_color_metric": "selectable: return_1d_pct, return_1m_pct, relative_volume",
            "request_time_per_symbol_fanout": False,
            "background_provider_call_budget": {
                "broad_observation_pages": broad_status.get("provider_call_count", 0),
                "sector_queries": (classification_contract.get("summary") or {}).get("provider_call_count", 0),
                "per_symbol_calls": 0,
            },
            "broker_execution_added": False,
            "non_advisory": True,
        },
        "summary": {
            "workspace": "market-map-screener",
            "instrument_count": len(rows),
            "ranked_count": len(ranked),
            "financial_coverage_count": sum(
                1 for row in rows if (row.get("factors") or {}).get("valuation_available") is True
            ),
            "official_listing_coverage_count": universe_contract["official_listing_coverage_count"],
            "official_listing_directory_count": universe_contract["official_listing_directory_count"],
            "taxonomy_coverage_count": universe_contract["taxonomy_coverage_count"],
            "unclassified_count": universe_contract["unclassified_count"],
            "rank_model_count": len(discovery["rank_models"]),
            "sector_count": len(sectors),
            "source_status": source_status if rows else "unavailable",
            "runtime_requested": bool(include_runtime),
            "not_financial_advice": True,
        },
        "caveat": "Ranks are descriptive research calculations, not recommendations or trade signals.",
    }
