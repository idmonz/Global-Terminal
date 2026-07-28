from __future__ import annotations

import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import pandas as pd

from . import equity_provider_breadth
from .research_snapshot import RESEARCH_SNAPSHOT_TTL_SECONDS, research_snapshot_cache_key
from .runtime_cache import RuntimeCacheRecord, fetch_json_with_cache, load_runtime_cache_record, save_runtime_cache_record
from .sec_edgar_provider import build_sec_company_facts_context
from .symbol_workstation import (
    build_symbol_capability_plan,
    build_symbol_workstation_contract,
    build_symbol_workstation_fixture_catalog,
    resolve_symbol,
)
from .technical_analysis import (
    compute_drawdown,
    compute_macd,
    compute_realized_vol,
    compute_rsi,
    compute_sma_ema,
)


SYMBOL_INTELLIGENCE_VERSION = "symbol_intelligence.v2"
FORMULA_VERSION = "phase5n.quant.v1"
PANEL_VERSION = "phase6c.panel.v4"
SYMBOL_DELIVERY_VERSION = "symbol_delivery.v1"
DELIVERY_PANELS = (
    "summary",
    "chart",
    "chart-core",
    "technicals",
    "financials",
    "news",
    "catalysts",
    "sources",
    "comparison",
)
ALLOWED_PANELS = ("trend", "momentum", "risk", "comparison", "financials", "news", "asset", "sources")
DEFAULT_PANELS = ("trend", "momentum", "risk", "news", "asset")
FINANCIAL_TTL_SECONDS = 21_600
NEWS_TTL_SECONDS = 900
DERIVATIVES_TTL_SECONDS = 300
PANEL_STALE_SECONDS = 86_400
_WORD = re.compile(r"[A-Z0-9]+")
_NAME_STOPWORDS = {
    "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "PLC", "LTD", "LIMITED",
    "HOLDINGS", "GROUP", "TRUST", "ETF", "SHARES", "THE", "AND", "CLASS",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if hasattr(value, "isoformat"):
        value = value.isoformat()
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def _datetime(value: Any) -> datetime | None:
    normalized = _iso(value)
    return datetime.fromisoformat(normalized) if normalized else None


def _last_number(series: Any) -> float | None:
    current = pd.to_numeric(series, errors="coerce").dropna()
    return float(current.iloc[-1]) if not current.empty else None


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(row) for row in value if isinstance(row, dict)]
    if hasattr(value, "to_dict"):
        try:
            return [dict(row) for row in value.to_dict(orient="records")]
        except Exception:
            return []
    return []


def normalize_panels(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    raw = value.split(",") if isinstance(value, str) else list(value or DEFAULT_PANELS)
    selected: list[str] = []
    for item in raw:
        current = str(item or "").strip().lower()
        if current in ALLOWED_PANELS and current not in selected:
            selected.append(current)
    return selected or list(DEFAULT_PANELS)


def panel_cache_key(
    panel: str,
    asset_class: str,
    symbol: str,
    interval: str,
    range_name: str,
    *,
    formula_version: str = PANEL_VERSION,
    compare: str | None = None,
) -> str:
    parts = ["symbol-intelligence", panel, asset_class, symbol, interval, range_name, formula_version]
    if compare:
        parts.append(compare)
    return ":".join(parts)


def build_market_clock(
    history: list[dict[str, Any]],
    *,
    asset_class: str,
    interval: str,
    source_status: str,
    retrieved_at: str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or _utc_now()
    last_observation = _datetime(history[-1].get("date")) if history else None
    age = max(0.0, (current - last_observation).total_seconds()) if last_observation else None
    normalized_source = str(source_status or "unavailable")

    if normalized_source == "fixture":
        status = "fixture"
        age = None
    elif normalized_source == "stale":
        status = "stale-cache"
    elif last_observation is None:
        status = "unavailable"
    elif asset_class == "crypto":
        interval_seconds = {"15m": 900, "1h": 3600, "4h": 14_400, "1d": 86_400}.get(interval, 3600)
        status = "intraday-current" if age is not None and age <= interval_seconds * 2.5 else "delayed-observation"
    elif interval == "1h":
        status = "intraday-current" if age is not None and age <= 4 * 3600 else "delayed-observation"
    else:
        status = "latest-session" if age is not None and age <= 5 * 86_400 else "delayed-observation"

    caveat = {
        "fixture": "Synthetic fixture timestamp; not a market observation.",
        "stale-cache": "The provider refresh failed or cache-only mode retained an older snapshot.",
        "latest-session": "Latest available closed-session bar; this is not an intraday real-time quote.",
        "intraday-current": "Latest available interval bar; exchange/provider latency can remain.",
        "delayed-observation": "The latest market observation is older than the interval/session tolerance.",
        "unavailable": "No verified market observation is available.",
    }[status]
    return {
        "retrieved_at": _iso(retrieved_at),
        "fetched_at": _iso(retrieved_at),
        "market_data_as_of": last_observation.isoformat() if last_observation else None,
        "observation_age_seconds": round(age, 3) if age is not None else None,
        "market_data_status": status,
        "source_status": normalized_source,
        "interval": interval,
        "timezone": "UTC",
        "real_time_quote_claimed": False,
        "caveat": caveat,
        "data_gap": None if last_observation else "No timestamped OHLCV observation.",
        "not_financial_advice": True,
    }


def _history_frame(history: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(history).copy()
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame.get("date"), errors="coerce", utc=True)
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame.get(column), errors="coerce")
    frame = frame.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date", keep="last")
    return frame.reset_index(drop=True)


def _series_points(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if frame.empty or column not in frame:
        return []
    return [
        {"x": row["date"].isoformat(), "y": float(row[column])}
        for _, row in frame[["date", column]].dropna().iterrows()
    ]


def compute_symbol_technicals(history: list[dict[str, Any]], *, interval: str) -> dict[str, Any]:
    frame = _history_frame(history)
    if frame.empty:
        return _empty_technical("No verified OHLCV history is available.")

    close = frame["close"]
    trend = compute_sma_ema(close, windows=(20, 50))
    rsi = compute_rsi(close, window=14)
    macd = compute_macd(close, fast=12, slow=26, signal=9)
    annualization = {"15m": 35_040, "1h": 8_760, "4h": 2_190, "1d": 252}.get(interval, 252)
    realized_vol = compute_realized_vol(close, window=20, annualization=annualization)
    drawdown = compute_drawdown(close)
    enriched = pd.concat([frame[["date", "close", "volume"]], trend, rsi.rename("rsi_14"), macd, realized_vol.rename("realized_volatility_20"), drawdown.rename("drawdown")], axis=1)

    enough_20 = len(frame) >= 20
    enough_50 = len(frame) >= 50
    status = "available" if enough_50 else "partial" if enough_20 else "insufficient-history"
    data_gap = None if status == "available" else "At least 50 observations are required for the full SMA/EMA set." if enough_20 else "At least 20 observations are required for trend and risk panels."
    summary = {
        "sma_20": _last_number(trend["sma_20"]) if enough_20 else None,
        "sma_50": _last_number(trend["sma_50"]) if enough_50 else None,
        "ema_20": _last_number(trend["ema_20"]) if enough_20 else None,
        "ema_50": _last_number(trend["ema_50"]) if enough_50 else None,
        "rsi_14": _last_number(rsi) if len(frame) >= 15 else None,
        "macd_12_26_9": _last_number(macd["macd"]) if len(frame) >= 26 else None,
        "macd_signal_9": _last_number(macd["signal"]) if len(frame) >= 26 else None,
        "macd_histogram": _last_number(macd["histogram"]) if len(frame) >= 26 else None,
        "realized_volatility_20": _last_number(realized_vol) if enough_20 else None,
        "drawdown": _last_number(drawdown),
    }
    series = {
        "sma_20": _series_points(enriched, "sma_20") if enough_20 else [],
        "sma_50": _series_points(enriched, "sma_50") if enough_50 else [],
        "ema_20": _series_points(enriched, "ema_20") if enough_20 else [],
        "ema_50": _series_points(enriched, "ema_50") if enough_50 else [],
        "rsi_14": _series_points(enriched, "rsi_14") if len(frame) >= 15 else [],
        "macd": _series_points(enriched, "macd") if len(frame) >= 26 else [],
        "macd_signal": _series_points(enriched, "signal") if len(frame) >= 26 else [],
        "macd_histogram": _series_points(enriched, "histogram") if len(frame) >= 26 else [],
        "realized_volatility_20": _series_points(enriched, "realized_volatility_20") if enough_20 else [],
        "drawdown": _series_points(enriched, "drawdown"),
    }
    formula_rows = [
        ("trend", "SMA(20/50); EMA span(20/50), adjust=False", 20),
        ("momentum", "RSI(14 rolling mean gain/loss); MACD EMA(12)-EMA(26), signal EMA(9)", 26),
        ("risk", f"20-observation return volatility annualized by sqrt({annualization}); running-peak drawdown", 20),
    ]
    source_register = [
        {
            "provider": "project-native/verified-history",
            "source": family,
            "source_url": None,
            "source_status": status,
            "fetched_at": history[-1].get("fetched_at") if history else None,
            "row_count": len(frame),
            "formula": formula,
            "minimum_observations": minimum,
            "caveat": "Calculated from the displayed verified close/volume history; no forecast or recommendation.",
            "data_gap": data_gap,
            "not_financial_advice": True,
        }
        for family, formula, minimum in formula_rows
    ]
    return {
        "status": status,
        "formula_version": FORMULA_VERSION,
        "observation_count": len(frame),
        "annualization_factor": annualization,
        "minimum_observations": {"rsi": 15, "macd": 26, "trend_short": 20, "trend_long": 50, "risk": 20},
        "summary": summary,
        "series": series,
        "source_register": source_register,
        "caveat": "Indicators describe historical observations only.",
        "data_gap": data_gap,
        "not_financial_advice": True,
    }


def _empty_technical(gap: str) -> dict[str, Any]:
    return {
        "status": "insufficient-history",
        "formula_version": FORMULA_VERSION,
        "observation_count": 0,
        "annualization_factor": None,
        "minimum_observations": {"rsi": 15, "macd": 26, "trend_short": 20, "trend_long": 50, "risk": 20},
        "summary": {key: None for key in ["sma_20", "sma_50", "ema_20", "ema_50", "rsi_14", "macd_12_26_9", "macd_signal_9", "macd_histogram", "realized_volatility_20", "drawdown"]},
        "series": {},
        "source_register": [],
        "caveat": "Indicators require verified history.",
        "data_gap": gap,
        "not_financial_advice": True,
    }


def align_comparison_history(
    primary: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    *,
    primary_symbol: str,
    comparison_symbol: str,
) -> dict[str, Any]:
    left = _history_frame(primary)[["date", "close"]].rename(columns={"close": "primary_close"}) if primary else pd.DataFrame()
    right = _history_frame(comparison)[["date", "close"]].rename(columns={"close": "comparison_close"}) if comparison else pd.DataFrame()
    if left.empty or right.empty:
        return _comparison_gap(primary_symbol, comparison_symbol, "One or both verified histories are unavailable.")
    merged = left.merge(right, on="date", how="inner").dropna()
    if len(merged) < 2:
        return _comparison_gap(primary_symbol, comparison_symbol, "Fewer than two overlapping timestamps are available.")
    primary_base = float(merged.iloc[0]["primary_close"])
    comparison_base = float(merged.iloc[0]["comparison_close"])
    if not primary_base or not comparison_base:
        return _comparison_gap(primary_symbol, comparison_symbol, "The first overlapping close is zero or invalid.")
    points = [
        {
            "x": row["date"].isoformat(),
            "primary_return_pct": (float(row["primary_close"]) / primary_base - 1) * 100,
            "comparison_return_pct": (float(row["comparison_close"]) / comparison_base - 1) * 100,
        }
        for _, row in merged.iterrows()
    ]
    return {
        "status": "available",
        "primary_symbol": primary_symbol,
        "comparison_symbol": comparison_symbol,
        "overlap_count": len(points),
        "alignment_method": "timestamp-inner-join",
        "normalization": "rebased-return-percent-from-first-overlap",
        "points": points,
        "caveat": "Comparison is based on aligned displayed closes and does not include dividends, FX conversion, fees, or corporate-action adjustments unless the source history does.",
        "data_gap": None,
        "not_financial_advice": True,
    }


def _comparison_gap(primary_symbol: str, comparison_symbol: str | None, gap: str) -> dict[str, Any]:
    return {
        "status": "unavailable" if comparison_symbol else "not_requested",
        "primary_symbol": primary_symbol,
        "comparison_symbol": comparison_symbol,
        "overlap_count": 0,
        "alignment_method": "timestamp-inner-join",
        "normalization": "rebased-return-percent-from-first-overlap",
        "points": [],
        "caveat": "Comparison requires two verified, compatible histories.",
        "data_gap": gap,
        "not_financial_advice": True,
    }


def _identity_terms(identity: dict[str, Any]) -> list[str]:
    symbol = str(identity.get("symbol") or "").upper()
    terms = {symbol}
    for alias in identity.get("aliases") or []:
        alias_text = str(alias or "").upper()
        if len(alias_text) >= 3:
            terms.add(alias_text)
    name_tokens = [token for token in _WORD.findall(str(identity.get("name") or "").upper()) if len(token) >= 4 and token not in _NAME_STOPWORDS]
    if name_tokens:
        terms.add(name_tokens[0])
    return sorted(terms, key=lambda value: (-len(value), value))


def filter_exact_symbol_news(rows: list[dict[str, Any]], identity: dict[str, Any], *, limit: int = 10) -> list[dict[str, Any]]:
    terms = _identity_terms(identity)
    matches = []
    seen = set()
    for row in rows:
        title = str(row.get("title") or "").strip()
        summary = str(row.get("summary") or row.get("description") or "").strip()
        haystack = title.upper()
        matched = [term for term in terms if re.search(rf"(?<![A-Z0-9]){re.escape(term)}(?![A-Z0-9])", haystack)]
        source_url = str(row.get("source_url") or row.get("url") or "").strip()
        dedupe = (title.lower(), source_url)
        if not title or not matched or dedupe in seen:
            continue
        seen.add(dedupe)
        matches.append({
            **row,
            "title": title,
            "summary": summary,
            "source_url": source_url or None,
            "match_terms": matched,
            "exact_symbol_scope": True,
            "not_financial_advice": True,
        })
        if len(matches) >= limit:
            break
    return matches


def _panel_from_cache_or_fetch(
    key: str,
    *,
    runtime_mode: str,
    ttl_seconds: int,
    provider: str,
    source_url: str,
    fetcher: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any] | None, str, str | None, str | None]:
    now = _utc_now()
    cached = load_runtime_cache_record(key)
    if cached and cached.age_seconds(now) <= ttl_seconds:
        return dict(cached.data or {}), "cached", None, cached.fetched_at_iso
    if runtime_mode == "cache":
        if cached and cached.age_seconds(now) <= PANEL_STALE_SECONDS:
            return dict(cached.data or {}), "stale", "Cache-only mode retained an older panel snapshot.", cached.fetched_at_iso
        return None, "unavailable", "No panel cache record is available; live refresh was not attempted.", None
    try:
        data = fetcher()
        record = RuntimeCacheRecord(
            key=key,
            data=data,
            source=provider,
            provider=provider,
            source_url=source_url,
            fetched_at=now,
        )
        save_runtime_cache_record(record)
        return data, "live/fresh", None, record.fetched_at_iso
    except Exception as exc:
        if cached and cached.age_seconds(now) <= PANEL_STALE_SECONDS:
            return dict(cached.data or {}), "stale", f"Live panel refresh failed; prior cache retained. {exc}", cached.fetched_at_iso
        return None, "unavailable", str(exc), now.isoformat()


def _normalize_statement(frame: Any, fields: list[str], *, limit: int = 4) -> list[dict[str, Any]]:
    if frame is None or getattr(frame, "empty", True):
        return []
    normalized = frame.copy().T
    normalized.index = pd.to_datetime(normalized.index, errors="coerce", utc=True)
    normalized = normalized.sort_index().tail(limit)
    rows = []
    for period, row in normalized.iterrows():
        output = {"period": period.isoformat() if not pd.isna(period) else None}
        for field in fields:
            output[field] = _number(row.get(field))
        rows.append(output)
    return rows


def _sec_identity(symbol: str) -> dict[str, Any]:
    user_agent = os.getenv("SEC_USER_AGENT")
    source_url = "https://www.sec.gov/files/company_tickers.json"
    if not user_agent:
        return {"availability": "missing-user-agent", "provider": "sec_edgar", "source_url": source_url, "cik": None, "title": None, "data_gap": "SEC_USER_AGENT is required; no secret value is exposed."}
    payload, status = fetch_json_with_cache(
        "phase5n:sec-company-tickers:v1",
        source_url,
        provider="sec_edgar",
        source="SEC company ticker registry",
        headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
        ttl_seconds=86_400,
        timeout=15,
    )
    for row in (payload or {}).values() if isinstance(payload, dict) else []:
        if isinstance(row, dict) and str(row.get("ticker") or "").upper() == symbol:
            cik = str(row.get("cik_str") or "").zfill(10)
            return {
                "availability": "available",
                "provider": "sec_edgar",
                "source_url": f"https://www.sec.gov/edgar/browse/?CIK={cik}",
                "cik": cik,
                "title": row.get("title"),
                "fetched_at": status.fetched_at.isoformat(),
                "source_status": "cached" if status.is_cached else "live/fresh",
                "data_gap": None,
            }
    return {"availability": "unavailable", "provider": "sec_edgar", "source_url": source_url, "cik": None, "title": None, "data_gap": status.error or "Symbol not found in the public SEC ticker registry."}


def _fetch_financial_context(identity: dict[str, Any]) -> dict[str, Any]:
    import yfinance as yf

    symbol = str(identity["provider_symbol"])
    ticker = yf.Ticker(symbol)
    info = dict(getattr(ticker, "info", {}) or {})
    if identity["asset_class"] == "etf":
        metrics = {
            "total_assets": _number(info.get("totalAssets")),
            "annual_report_expense_ratio": _number(info.get("annualReportExpenseRatio")),
            "yield": _number(info.get("yield")),
            "beta_3y": _number(info.get("beta3Year")),
            "fund_family": info.get("fundFamily"),
            "category": info.get("category"),
        }
        if not any(value not in (None, "") for value in metrics.values()):
            raise RuntimeError("No usable ETF profile fields returned.")
        return {"metrics": metrics, "statements": {}, "sec_identity": None, "sec_facts": _not_applicable_context("SEC company facts do not apply to fund profiles.")}

    metrics = {
        "market_cap": _number(info.get("marketCap")),
        "trailing_pe": _number(info.get("trailingPE")),
        "forward_pe": _number(info.get("forwardPE")),
        "price_to_sales": _number(info.get("priceToSalesTrailing12Months")),
        "price_to_book": _number(info.get("priceToBook")),
        "enterprise_to_ebitda": _number(info.get("enterpriseToEbitda")),
        "profit_margin": _number(info.get("profitMargins")),
        "operating_margin": _number(info.get("operatingMargins")),
        "return_on_equity": _number(info.get("returnOnEquity")),
        "revenue_growth": _number(info.get("revenueGrowth")),
        "free_cash_flow": _number(info.get("freeCashflow")),
        "total_debt": _number(info.get("totalDebt")),
        "cash": _number(info.get("totalCash")),
    }
    statements = {
        "income": _normalize_statement(getattr(ticker, "income_stmt", None), ["Total Revenue", "Operating Income", "Net Income", "Diluted EPS"]),
        "balance": _normalize_statement(getattr(ticker, "balance_sheet", None), ["Total Assets", "Total Debt", "Cash And Cash Equivalents", "Stockholders Equity"]),
        "cashflow": _normalize_statement(getattr(ticker, "cashflow", None), ["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow"]),
    }
    if not any(value is not None for value in metrics.values()) and not any(statements.values()):
        raise RuntimeError("No usable company financial fields returned.")
    identity_cik = str(identity.get("cik") or "").zfill(10) if identity.get("cik") else None
    sec_identity = (
        {
            "availability": "available",
            "provider": "sec_edgar",
            "source_url": f"https://www.sec.gov/edgar/browse/?CIK={identity_cik}",
            "cik": identity_cik,
            "title": identity.get("name"),
            "fetched_at": identity.get("reviewed_at"),
            "source_status": identity.get("sec_source_status") or "official/materialized",
            "data_gap": None,
        }
        if identity_cik
        else _sec_identity(str(identity["symbol"]))
    )
    sec_facts = (
        build_sec_company_facts_context(str(sec_identity["cik"]))
        if sec_identity.get("cik")
        else {
            "availability": "unavailable",
            "provider": "sec_edgar",
            "source_status": "unavailable",
            "source_url": sec_identity.get("source_url"),
            "fetched_at": sec_identity.get("fetched_at"),
            "cik": None,
            "entity_name": None,
            "facts": [],
            "fact_count": 0,
            "source_register": [{
                "provider": "sec_edgar",
                "source": "SEC XBRL companyfacts",
                "source_url": sec_identity.get("source_url"),
                "source_status": "unavailable",
                "fetched_at": sec_identity.get("fetched_at"),
                "row_count": 0,
                "caveat": "SEC identity is required before company facts can be requested.",
                "data_gap": sec_identity.get("data_gap"),
                "not_financial_advice": True,
            }],
            "caveat": "SEC identity is required before company facts can be requested.",
            "data_gap": sec_identity.get("data_gap"),
            "not_financial_advice": True,
        }
    )
    return {
        "metrics": metrics,
        "statements": statements,
        "sec_identity": sec_identity,
        "sec_facts": sec_facts,
    }


def _market_snapshot_metrics(identity: dict[str, Any]) -> dict[str, Any]:
    context = identity.get("market_map_context") if isinstance(identity.get("market_map_context"), dict) else {}
    factors = context.get("factors") if isinstance(context.get("factors"), dict) else {}
    return {
        "market_cap": _number(factors.get("market_cap") or context.get("market_cap")),
        "trailing_pe": _number(factors.get("trailing_pe")),
        "forward_pe": _number(factors.get("forward_pe")),
        "price_to_book": _number(factors.get("price_to_book")),
        "eps_ttm": _number(factors.get("eps_ttm")),
        "eps_forward": _number(factors.get("eps_forward")),
    }


def _cache_only_provider_context(kind: str) -> dict[str, Any]:
    return {
        "availability": "unavailable",
        "provider": "cache-only",
        "source_status": "unavailable",
        "source_url": None,
        "fetched_at": None,
        "metrics": {},
        "rows": [],
        "source_register": [],
        "caveat": f"{kind} provider refresh is disabled in cache mode.",
        "data_gap": f"No cached {kind.lower()} provider context is available.",
        "not_financial_advice": True,
    }


def _financial_context(identity: dict[str, Any], runtime_mode: str, interval: str, range_name: str) -> dict[str, Any]:
    if identity["asset_class"] == "crypto":
        return {"availability": "not_applicable", "context_type": "not_applicable", "company_statements_applicable": False, "source_status": "not_applicable", "metrics": {}, "statements": {}, "sec_identity": None, "sec_facts": _not_applicable_context("SEC company facts do not apply to a crypto pair."), "earnings_calendar": _not_applicable_context("Company earnings do not apply to a crypto pair."), "provider_breadth": None, "source_register": [], "caveat": "Company financial statements do not apply to a crypto pair.", "data_gap": None, "not_financial_advice": True}
    context_type = "fund-profile" if identity["asset_class"] == "etf" else "company-financials"
    if runtime_mode == "fixture":
        return {
            "availability": "fixture-taxonomy-only",
            "context_type": context_type,
            "company_statements_applicable": identity["asset_class"] == "equity",
            "source_status": "fixture",
            "provider": "phase5n.financial_fixture",
            "fetched_at": "2026-06-22T00:00:00+00:00",
            "metrics": {},
            "statements": {},
            "sec_identity": None,
            "sec_facts": _fixture_context("SEC company facts are not embedded in deterministic fixtures."),
            "earnings_calendar": _fixture_context("Earnings/calendar rows are not embedded in deterministic fixtures."),
            "provider_breadth": None,
            "source_register": [],
            "caveat": "Deterministic fixture contains no current statements, ratios, fund holdings, or estimates.",
            "data_gap": "Use live-if-available mode for public provider availability.",
            "not_financial_advice": True,
        }
    key = panel_cache_key("financials", identity["asset_class"], identity["symbol"], interval, range_name, formula_version=PANEL_VERSION)
    source_url = f"https://finance.yahoo.com/quote/{quote(identity['provider_symbol'])}"
    data, status, gap, fetched_at = _panel_from_cache_or_fetch(key, runtime_mode=runtime_mode, ttl_seconds=FINANCIAL_TTL_SECONDS, provider="yfinance + SEC EDGAR", source_url=source_url, fetcher=lambda: _fetch_financial_context(identity))
    provider_breadth = (
        equity_provider_breadth.build_equity_provider_breadth(identity)
        if identity["asset_class"] == "equity" and runtime_mode == "live-if-available"
        else _cache_only_provider_context("Equity profile")
        if identity["asset_class"] == "equity"
        else None
    )
    earnings = (
        equity_provider_breadth.build_equity_earnings_context(identity)
        if identity["asset_class"] == "equity" and runtime_mode == "live-if-available"
        else _cache_only_provider_context("Earnings")
        if identity["asset_class"] == "equity"
        else _not_applicable_context("Company earnings do not apply to fund profiles.")
    )
    sec_facts = (data or {}).get("sec_facts") or {
        "availability": "unavailable",
        "provider": "sec_edgar",
        "source_status": "unavailable",
        "facts": [],
        "source_register": [],
        "data_gap": "No cached or live SEC company facts context is available.",
    }
    snapshot_metrics = {
        metric: value
        for metric, value in _market_snapshot_metrics(identity).items()
        if value is not None
    }
    combined_metrics = {
        **snapshot_metrics,
        **dict((data or {}).get("metrics", {})),
    }
    if provider_breadth:
        combined_metrics.update(provider_breadth.get("metrics") or {})
    combined_gap = "; ".join([
        str(item) for item in [
            gap,
            (provider_breadth or {}).get("data_gap"),
            sec_facts.get("data_gap") if isinstance(sec_facts, dict) else None,
            earnings.get("data_gap"),
        ] if item
    ]) or None
    market_context = identity.get("market_map_context") if isinstance(identity.get("market_map_context"), dict) else {}
    snapshot_sources = (
        [
            {
                "provider": market_context.get("market_provider") or "market_snapshot_store",
                "source": f"{identity['symbol']} materialized financial snapshot",
                "source_url": market_context.get("market_source_url"),
                "source_status": identity.get("snapshot_status") or "cached/materialized",
                "fetched_at": market_context.get("market_fetched_at") or identity.get("snapshot_created_at"),
                "row_count": len(snapshot_metrics),
                "caveat": "Delayed materialized valuation fields are retained independently from on-demand company financials.",
                "data_gap": market_context.get("data_gap"),
                "not_financial_advice": True,
            }
        ]
        if snapshot_metrics
        else []
    )
    source_register = [
        *snapshot_sources,
        *list((provider_breadth or {}).get("source_register") or []),
        *(list(sec_facts.get("source_register") or []) if isinstance(sec_facts, dict) else []),
        *list(earnings.get("source_register") or []),
    ]
    return {
        "availability": (
            "available"
            if data or (provider_breadth or {}).get("availability") == "available"
            else "market-snapshot-only"
            if snapshot_metrics
            else "unavailable"
        ),
        "context_type": context_type,
        "company_statements_applicable": identity["asset_class"] == "equity",
        "source_status": status if data else identity.get("snapshot_status") or status,
        "provider": "yfinance + SEC EDGAR" if data else market_context.get("market_provider") or "market_snapshot_store",
        "source_url": source_url if data else market_context.get("market_source_url"),
        "fetched_at": fetched_at if data else market_context.get("market_fetched_at") or identity.get("snapshot_created_at"),
        "metrics": combined_metrics,
        "statements": (data or {}).get("statements", {}),
        "sec_identity": (data or {}).get("sec_identity"),
        "sec_facts": sec_facts,
        "earnings_calendar": earnings,
        "provider_breadth": provider_breadth,
        "source_register": source_register,
        "caveat": "Free public adapter, SEC identity availability, and optional Alpha Vantage/Finnhub breadth; estimates, target prices, authoritative fund holdings, and licensed reference data are not claimed.",
        "data_gap": combined_gap,
        "not_financial_advice": True,
    }


def _fixture_context(gap: str) -> dict[str, Any]:
    return {
        "availability": "fixture-unavailable",
        "provider": "phase6a.fixture",
        "source_status": "fixture",
        "source_url": None,
        "fetched_at": "2026-06-22T00:00:00+00:00",
        "facts": [],
        "rows": [],
        "source_register": [],
        "caveat": "No current value is synthesized in fixture mode.",
        "data_gap": gap,
        "not_financial_advice": True,
    }


def _not_applicable_context(caveat: str) -> dict[str, Any]:
    return {
        "availability": "not_applicable",
        "provider": "not_applicable",
        "source_status": "not_applicable",
        "source_url": None,
        "fetched_at": None,
        "facts": [],
        "rows": [],
        "source_register": [],
        "caveat": caveat,
        "data_gap": None,
        "not_financial_advice": True,
    }


def _normalize_yfinance_news(identity: dict[str, Any]) -> list[dict[str, Any]]:
    import yfinance as yf

    provider_symbol = str(identity["provider_symbol"])
    if identity["asset_class"] == "crypto":
        provider_symbol = f"{identity.get('base_asset')}-USD"
    raw = yf.Ticker(provider_symbol).news or []
    rows = []
    for item in raw:
        content = item.get("content") if isinstance(item, dict) and isinstance(item.get("content"), dict) else item
        if not isinstance(content, dict):
            continue
        canonical = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
        provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
        rows.append({
            "title": content.get("title"),
            "summary": content.get("summary") or content.get("description"),
            "published_at": _iso(content.get("pubDate") or content.get("displayTime")),
            "source_url": canonical.get("url") or content.get("clickThroughUrl"),
            "provider": provider.get("displayName") or "Yahoo Finance news",
            "aggregator": "yfinance/Yahoo Finance",
        })
    return filter_exact_symbol_news(rows, identity)


def _exact_news(identity: dict[str, Any], runtime_mode: str, interval: str, range_name: str) -> dict[str, Any]:
    if runtime_mode == "fixture":
        return {"availability": "fixture-unavailable", "source_status": "fixture", "provider": "phase5n.news_fixture", "fetched_at": "2026-06-22T00:00:00+00:00", "rows": [], "match_terms": _identity_terms(identity), "source_register": [], "caveat": "No headline is fabricated for the fixture.", "data_gap": "Live/cache exact-symbol news was not requested.", "not_financial_advice": True}
    key = panel_cache_key("exact-news", identity["asset_class"], identity["symbol"], interval, range_name, formula_version=PANEL_VERSION)
    source_url = f"https://finance.yahoo.com/quote/{quote(identity['provider_symbol'])}/news"
    data, status, gap, fetched_at = _panel_from_cache_or_fetch(key, runtime_mode=runtime_mode, ttl_seconds=NEWS_TTL_SECONDS, provider="yfinance/Yahoo Finance news", source_url=source_url, fetcher=lambda: {"rows": _normalize_yfinance_news(identity)})
    yahoo_rows = [
        {
            **row,
            "source_status": status,
            "fetched_at": fetched_at,
            "freshness": status,
            "caveat": "The title matched a bounded symbol or identity term; verify the linked publisher source.",
            "data_gap": None,
        }
        for row in list((data or {}).get("rows") or [])
    ]
    supplemental = (
        equity_provider_breadth.build_equity_news_context(identity)
        if identity["asset_class"] == "equity" and runtime_mode == "live-if-available"
        else _cache_only_provider_context("Exact news")
        if identity["asset_class"] == "equity"
        else None
    )
    rows = _dedupe_news_rows([*yahoo_rows, *list((supplemental or {}).get("rows") or [])])
    combined_gap = "; ".join([item for item in [gap if data is None else None, (supplemental or {}).get("data_gap")] if item]) or None
    return {
        "availability": "available" if rows else "exact-news-empty" if data is not None else "unavailable",
        "source_status": "live/fresh" if any(str(row.get("source_status")) == "live/fresh" for row in rows) else status,
        "provider": "yfinance/Yahoo Finance news + optional Alpha Vantage/Finnhub",
        "source_url": source_url,
        "fetched_at": fetched_at,
        "rows": rows,
        "match_terms": _identity_terms(identity),
        "source_register": (supplemental or {}).get("source_register", []),
        "caveat": "Only bounded title matches for the canonical symbol or identity token are retained.",
        "data_gap": combined_gap if rows else combined_gap or "No exact symbol/name match in the returned provider set.",
        "not_financial_advice": True,
    }


def _dedupe_news_rows(rows: list[dict[str, Any]], *, limit: int = 12) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: str(item.get("published_at") or ""), reverse=True):
        key = str(row.get("source_url") or row.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(row)
        if len(output) >= limit:
            break
    return output


def _fetch_crypto_derivatives(symbol: str, interval: str) -> dict[str, Any]:
    from .crypto_derivatives import build_derivatives_snapshot

    period = interval if interval in {"5m", "15m", "1h", "4h", "1d"} else "1h"
    snapshot, status = build_derivatives_snapshot(symbol, period=period)
    if not snapshot or not status.ok:
        raise RuntimeError(status.error or "No usable Binance derivatives snapshot returned.")
    return {**snapshot, "provider_fetched_at": status.fetched_at.isoformat(), "provider_cached": bool(status.is_cached)}


def _crypto_derivatives(identity: dict[str, Any], runtime_mode: str, interval: str, range_name: str) -> dict[str, Any]:
    if identity["asset_class"] != "crypto":
        return {"availability": "not_applicable", "source_status": "not_applicable", "liquidation_coverage": "not_applicable", "metrics": {}, "caveat": "Crypto futures context does not apply to this asset class.", "data_gap": None, "not_financial_advice": True}
    if runtime_mode == "fixture":
        return {"availability": "fixture-unavailable", "source_status": "fixture", "provider": "phase5n.derivatives_fixture", "liquidation_coverage": "unavailable", "metrics": {}, "caveat": "No current derivatives value is synthesized in fixture mode.", "data_gap": "Use live-if-available mode for public Binance rows.", "not_financial_advice": True}
    key = panel_cache_key("crypto-derivatives", "crypto", identity["symbol"], interval, range_name, formula_version=PANEL_VERSION)
    source_url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={quote(identity['symbol'])}"
    data, status, gap, fetched_at = _panel_from_cache_or_fetch(key, runtime_mode=runtime_mode, ttl_seconds=DERIVATIVES_TTL_SECONDS, provider="Binance USD-M Futures", source_url=source_url, fetcher=lambda: _fetch_crypto_derivatives(identity["symbol"], interval))
    mark = _number((data or {}).get("mark_price"))
    index = _number((data or {}).get("index_price"))
    basis = (mark / index - 1) * 100 if mark and index else _number((data or {}).get("premium_pct"))
    metrics = {
        "mark_price": mark,
        "index_price": index,
        "basis_pct": basis,
        "funding_rate": _number((data or {}).get("funding_rate")),
        "open_interest_contracts": _number((data or {}).get("open_interest")),
        "taker_buy_sell_ratio": _number((data or {}).get("taker_buy_sell_ratio")),
    }
    return {
        "availability": "available" if any(value is not None for value in metrics.values()) else "unavailable",
        "source_status": status,
        "provider": "Binance USD-M Futures",
        "source_url": source_url,
        "fetched_at": (data or {}).get("provider_fetched_at") or fetched_at,
        "liquidation_coverage": "unavailable",
        "metrics": metrics,
        "caveat": "Futures mark, index, funding, basis, and open interest are distinct public exchange observations; they are not spot prices or account positioning.",
        "data_gap": gap or (data or {}).get("data_gaps"),
        "not_financial_advice": True,
    }


def _comparison(
    identity: dict[str, Any],
    history: list[dict[str, Any]],
    compare: str | None,
    *,
    interval: str,
    range_name: str,
    runtime_mode: str,
    snapshot_base_dir: str | Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not compare:
        return _comparison_gap(identity["symbol"], None, "No comparison symbol requested."), []
    compare_identity = resolve_symbol(compare, snapshot_base_dir=snapshot_base_dir)
    if compare_identity is None or compare_identity["symbol"] == identity["symbol"]:
        return _comparison_gap(identity["symbol"], compare, "Comparison symbol is unknown or identical to the primary symbol."), []
    contract = build_symbol_workstation_contract(
        compare_identity["symbol"],
        asset_class=compare_identity["asset_class"],
        interval=interval,
        range_name=range_name,
        runtime_mode=runtime_mode,
        snapshot_base_dir=snapshot_base_dir,
    )
    workstation = (contract.get("workstations") or [{}])[0]
    comparison_history = workstation.get("history") or []
    aligned = align_comparison_history(history, comparison_history, primary_symbol=identity["symbol"], comparison_symbol=compare_identity["symbol"])
    source_rows = workstation.get("source_register") or []
    return aligned, source_rows


def _price_chart(
    workstation: dict[str, Any],
    technicals: dict[str, Any],
    comparison: dict[str, Any],
    chart_type: str,
) -> dict[str, Any]:
    identity = workstation["identity"]
    history = workstation.get("history") or []
    series = [{"name": "Close", "points": [{"x": row["date"], "y": row["close"]} for row in history if row.get("close") is not None]}]
    technical_series = technicals.get("series") or {}
    for key, label in [("sma_20", "SMA 20"), ("ema_20", "EMA 20"), ("sma_50", "SMA 50")]:
        if technical_series.get(key):
            series.append({"name": label, "points": technical_series[key]})
    return {
        "chart_id": f"{identity['symbol']}.phase5n.price-volume",
        "chart_type": "symbol-candlestick" if chart_type == "candlestick" else "symbol-line",
        "active_type": chart_type,
        "title": f"{identity['symbol']} verified OHLCV",
        "symbol": identity["symbol"],
        "interval": workstation["request"].get("effective_interval"),
        "range": workstation["request"].get("effective_range"),
        "timezone": "UTC",
        "units": identity["currency"],
        "height_px": 430,
        "series": series,
        "candles": [{"time": row["date"], "open": row.get("open"), "high": row.get("high"), "low": row.get("low"), "close": row.get("close")} for row in history if all(row.get(key) is not None for key in ["open", "high", "low", "close"])],
        "volume": [{"time": row["date"], "value": row.get("volume"), "direction": "up" if (row.get("close") or 0) >= (row.get("open") or 0) else "down"} for row in history if row.get("volume") is not None],
        "comparison_overlap_count": comparison.get("overlap_count", 0),
        "provider": workstation["quote"].get("provider"),
        "source_status": workstation["quote"].get("source_status"),
        "fetched_at": workstation["quote"].get("fetched_at"),
        "caveat": workstation["quote"].get("caveat"),
        "data_gap": workstation["quote"].get("data_gap"),
        "not_financial_advice": True,
    }


def _analysis_charts(symbol: str, technicals: dict[str, Any], comparison: dict[str, Any]) -> list[dict[str, Any]]:
    series = technicals.get("series") or {}
    charts = [
        {"chart_id": f"{symbol}.rsi", "chart_type": "indicator-line", "title": "RSI 14", "height_px": 180, "series": [{"name": "RSI 14", "points": series.get("rsi_14", [])}], "source_status": technicals.get("status"), "formula": "RSI(14 rolling mean gain/loss)", "not_financial_advice": True},
        {"chart_id": f"{symbol}.macd", "chart_type": "indicator-line", "title": "MACD 12 / 26 / 9", "height_px": 180, "series": [{"name": "MACD", "points": series.get("macd", [])}, {"name": "Signal", "points": series.get("macd_signal", [])}], "source_status": technicals.get("status"), "formula": "EMA(12)-EMA(26); signal EMA(9)", "not_financial_advice": True},
        {"chart_id": f"{symbol}.risk", "chart_type": "indicator-line", "title": "Volatility / Drawdown", "height_px": 180, "series": [{"name": "Realized vol", "points": series.get("realized_volatility_20", [])}, {"name": "Drawdown", "points": series.get("drawdown", [])}], "source_status": technicals.get("status"), "formula": "20-observation annualized volatility; running-peak drawdown", "not_financial_advice": True},
    ]
    if comparison.get("status") == "available":
        charts.append({
            "chart_id": f"{symbol}.comparison",
            "chart_type": "indicator-line",
            "title": f"Normalized return vs {comparison['comparison_symbol']}",
            "height_px": 180,
            "series": [
                {"name": symbol, "points": [{"x": row["x"], "y": row["primary_return_pct"]} for row in comparison["points"]]},
                {"name": comparison["comparison_symbol"], "points": [{"x": row["x"], "y": row["comparison_return_pct"]} for row in comparison["points"]]},
            ],
            "source_status": "available",
            "formula": comparison["normalization"],
            "not_financial_advice": True,
        })
    return charts


def _enrich_workstation(
    workstation: dict[str, Any],
    *,
    runtime_mode: str,
    chart_type: str,
    panels: list[str],
    compare: str | None,
    snapshot_base_dir: str | Path | None = None,
) -> dict[str, Any]:
    identity = workstation["identity"]
    request = workstation["request"]
    history = workstation.get("history") or []
    interval = str(request.get("effective_interval") or request.get("requested_interval") or "1d")
    range_name = str(request.get("effective_range") or request.get("requested_range") or "3mo")
    base_status = str(workstation.get("summary", {}).get("status") or "")
    provider_runtime_mode = (
        "cache"
        if base_status in {"unsupported-interval", "unsupported-range"}
        else runtime_mode
    )
    technicals = compute_symbol_technicals(history, interval=interval)
    comparison, comparison_sources = _comparison(
        identity,
        history,
        compare,
        interval=interval,
        range_name=range_name,
        runtime_mode=provider_runtime_mode,
        snapshot_base_dir=snapshot_base_dir,
    )
    financial = _financial_context(identity, provider_runtime_mode, interval, range_name)
    news = _exact_news(identity, provider_runtime_mode, interval, range_name)
    derivatives = _crypto_derivatives(identity, provider_runtime_mode, interval, range_name)
    clock = build_market_clock(history, asset_class=identity["asset_class"], interval=interval, source_status=workstation["quote"].get("source_status"), retrieved_at=workstation["quote"].get("fetched_at"))
    price_chart = _price_chart(workstation, technicals, comparison, chart_type)
    analysis_charts = _analysis_charts(identity["symbol"], technicals, comparison)
    source_register = [
        *workstation.get("source_register", []),
        *technicals.get("source_register", []),
        {
            "provider": financial.get("provider", "not_applicable"), "source": "financial-context", "source_url": financial.get("source_url"), "source_status": financial.get("source_status"), "fetched_at": financial.get("fetched_at"), "row_count": len(financial.get("metrics") or {}), "caveat": financial.get("caveat"), "data_gap": financial.get("data_gap"), "not_financial_advice": True,
        },
        *list(financial.get("source_register") or []),
        {
            "provider": news.get("provider"), "source": "exact-symbol-news", "source_url": news.get("source_url"), "source_status": news.get("source_status"), "fetched_at": news.get("fetched_at"), "row_count": len(news.get("rows") or []), "caveat": news.get("caveat"), "data_gap": news.get("data_gap"), "not_financial_advice": True,
        },
        *list(news.get("source_register") or []),
        {
            "provider": derivatives.get("provider", "not_applicable"), "source": "crypto-derivatives", "source_url": derivatives.get("source_url"), "source_status": derivatives.get("source_status"), "fetched_at": derivatives.get("fetched_at"), "row_count": len([value for value in (derivatives.get("metrics") or {}).values() if value is not None]), "caveat": derivatives.get("caveat"), "data_gap": derivatives.get("data_gap"), "not_financial_advice": True,
        },
        *comparison_sources,
    ]
    panel_readiness = {
        "price-volume": "available" if history else "unavailable",
        "trend": technicals["status"],
        "momentum": technicals["status"],
        "risk": technicals["status"],
        "comparison": comparison["status"],
        "financials": financial["availability"],
        "news": news["availability"],
        "asset": derivatives["availability"] if identity["asset_class"] == "crypto" else financial["availability"],
        "sources": "available",
    }
    unavailable = [row for row in source_register if str(row.get("source_status")) in {"unavailable", "missing-key", "provider-error"} or row.get("data_gap") and not row.get("row_count")]
    return {
        **workstation,
        "capability_plan": build_symbol_capability_plan(
            identity,
            interval=interval,
            range_name=range_name,
            compare=compare,
        ),
        "market_clock": clock,
        "chart_views": {"active_type": chart_type, "available_types": ["line", "candlestick"], "price": price_chart, "analysis": analysis_charts},
        "chart_specs": [price_chart, *analysis_charts],
        "technical_analysis": technicals,
        "comparison": comparison,
        "financial_context": financial,
        "exact_news": news,
        "crypto_derivatives": derivatives,
        "news": news.get("rows") or [],
        "panel_readiness": panel_readiness,
        "selected_panels": panels,
        "source_register": source_register,
        "unavailable_sources": unavailable,
        "summary": {
            **workstation["summary"],
            "market_data_status": clock["market_data_status"],
            "market_data_as_of": clock["market_data_as_of"],
            "retrieved_at": clock["retrieved_at"],
            "fetched_at": clock["retrieved_at"],
            "technical_status": technicals["status"],
            "exact_news_count": len(news.get("rows") or []),
            "comparison_overlap_count": comparison.get("overlap_count", 0),
            "chart_type": chart_type,
        },
    }


def _not_loaded_panel(panel: str) -> dict[str, Any]:
    return {
        "availability": "not-loaded",
        "status": "not-loaded",
        "source_status": "not-loaded",
        "provider": "on-demand-panel",
        "source_url": None,
        "fetched_at": None,
        "metrics": {},
        "statements": {},
        "facts": [],
        "rows": [],
        "source_register": [],
        "caveat": f"{panel} is delivered only when its exact panel endpoint is requested.",
        "data_gap": None,
        "not_financial_advice": True,
    }


def _catalyst_context(identity: dict[str, Any], runtime_mode: str) -> dict[str, Any]:
    symbol = str(identity.get("symbol") or "").upper()
    asset_class = str(identity.get("asset_class") or "").lower()
    if runtime_mode == "fixture":
        return {
            "symbol": symbol,
            "availability": "fixture-unavailable",
            "source_status": "fixture",
            "fetched_at": None,
            "earnings": [],
            "dividends": [],
            "news": [],
            "next_event": None,
            "source_register": [],
            "caveat": "Fixture Watchlist catalysts remain in the fixture contract.",
            "data_gap": "Provider cache is not mixed into fixture-mode exact panels.",
            "not_financial_advice": True,
        }
    record = load_runtime_cache_record(research_snapshot_cache_key(asset_class, symbol))
    if record is None or not isinstance(record.data, dict):
        return {
            "symbol": symbol,
            "availability": "unavailable",
            "source_status": "unavailable",
            "fetched_at": None,
            "earnings": [],
            "dividends": [],
            "news": [],
            "next_event": None,
            "source_register": [],
            "caveat": "Catalysts are delivered from the bounded active-list research snapshot only.",
            "data_gap": "No exact-symbol Research Snapshot cache is available.",
            "not_financial_advice": True,
        }
    snapshot = dict(record.data)
    if str(snapshot.get("symbol") or "").upper() != symbol:
        return {
            "symbol": symbol,
            "availability": "unavailable",
            "source_status": "unavailable",
            "fetched_at": None,
            "earnings": [],
            "dividends": [],
            "news": [],
            "next_event": None,
            "source_register": [],
            "caveat": "Cross-symbol snapshot substitution is forbidden.",
            "data_gap": "The cached snapshot identity did not match the requested symbol.",
            "not_financial_advice": True,
        }
    catalysts = (
        dict(snapshot.get("catalysts"))
        if isinstance(snapshot.get("catalysts"), dict)
        else {}
    )
    freshness = "cached" if record.is_fresh(RESEARCH_SNAPSHOT_TTL_SECONDS) else "stale"
    return {
        **catalysts,
        "symbol": symbol,
        "availability": catalysts.get("availability") or "unavailable",
        "source_status": freshness if freshness == "stale" else catalysts.get("source_status") or freshness,
        "fetched_at": record.fetched_at_iso,
        "source_register": list(snapshot.get("source_register") or []),
        "caveat": catalysts.get("caveat") or "Catalysts are informational provider events.",
        "data_gap": catalysts.get("data_gap"),
        "not_financial_advice": True,
    }


def _delivery_shell(
    workstation: dict[str, Any],
    *,
    delivery: str,
    runtime_mode: str,
    chart_type: str,
    compare: str | None,
    snapshot_base_dir: str | Path | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    identity = workstation["identity"]
    request = workstation["request"]
    history = list(workstation.get("history") or [])
    interval = str(request.get("effective_interval") or request.get("requested_interval") or "1d")
    range_name = str(request.get("effective_range") or request.get("requested_range") or "3mo")
    clock = build_market_clock(
        history,
        asset_class=str(identity["asset_class"]),
        interval=interval,
        source_status=str(workstation.get("quote", {}).get("source_status") or "unavailable"),
        retrieved_at=workstation.get("quote", {}).get("fetched_at"),
    )
    financial = _not_loaded_panel("Financials")
    news = _not_loaded_panel("Exact news")
    catalysts = _not_loaded_panel("Catalysts")
    derivatives = _not_loaded_panel("Crypto derivatives")
    technicals = _empty_technical("Technical calculations are delivered with the chart panel.")
    comparison = _comparison_gap(str(identity["symbol"]), compare, "Comparison is delivered only when requested.")
    chart_views: dict[str, Any] = {
        "active_type": chart_type,
        "available_types": ["line", "candlestick"],
        "price": {},
        "analysis": [],
    }
    source_register = list(workstation.get("source_register") or [])
    delivered_history: list[dict[str, Any]] = []

    if delivery in {"chart", "chart-core", "technicals", "comparison"}:
        technicals = compute_symbol_technicals(history, interval=interval)
        comparison_sources: list[dict[str, Any]] = []
        if delivery in {"chart", "comparison"}:
            comparison, comparison_sources = _comparison(
                identity,
                history,
                compare if delivery == "comparison" or compare else None,
                interval=interval,
                range_name=range_name,
                runtime_mode=runtime_mode,
                snapshot_base_dir=snapshot_base_dir,
            )
        if delivery == "chart-core":
            chart_views = {
                "active_type": chart_type,
                "available_types": ["line", "candlestick"],
                "price": _price_chart(workstation, technicals, comparison, chart_type),
                "analysis": [],
            }
            technicals = {
                **technicals,
                "series": {},
                "caveat": (
                    "Indicator overlays are embedded in the compact price chart; "
                    "full indicator series are delivered by the technicals panel."
                ),
            }
        elif delivery == "technicals":
            chart_views = {
                "active_type": chart_type,
                "available_types": ["line", "candlestick"],
                "price": {},
                "analysis": _analysis_charts(str(identity["symbol"]), technicals, comparison),
            }
            technicals = {**technicals, "series": {}}
        else:
            chart_views = {
                "active_type": chart_type,
                "available_types": ["line", "candlestick"],
                "price": _price_chart(workstation, technicals, comparison, chart_type),
                "analysis": _analysis_charts(str(identity["symbol"]), technicals, comparison),
            }
        source_register.extend(technicals.get("source_register") or [])
        source_register.extend(comparison_sources)
        delivered_history = history if delivery in {"chart", "comparison"} else []
    elif delivery == "financials":
        financial = _financial_context(identity, runtime_mode, interval, range_name)
        source_register.append(
            {
                "provider": financial.get("provider"),
                "source": "financial-context",
                "source_url": financial.get("source_url"),
                "source_status": financial.get("source_status"),
                "fetched_at": financial.get("fetched_at"),
                "row_count": len(financial.get("metrics") or {}),
                "caveat": financial.get("caveat"),
                "data_gap": financial.get("data_gap"),
                "not_financial_advice": True,
            }
        )
        source_register.extend(financial.get("source_register") or [])
    elif delivery == "news":
        news = _exact_news(identity, runtime_mode, interval, range_name)
        source_register.append(
            {
                "provider": news.get("provider"),
                "source": "exact-symbol-news",
                "source_url": news.get("source_url"),
                "source_status": news.get("source_status"),
                "fetched_at": news.get("fetched_at"),
                "row_count": len(news.get("rows") or []),
                "caveat": news.get("caveat"),
                "data_gap": news.get("data_gap"),
                "not_financial_advice": True,
            }
        )
        source_register.extend(news.get("source_register") or [])
    elif delivery == "catalysts":
        catalysts = _catalyst_context(identity, runtime_mode)
        source_register.append(
            {
                "provider": "watchlist-research-snapshot",
                "source": f"{identity['symbol']} catalysts",
                "source_url": None,
                "source_status": catalysts.get("source_status"),
                "fetched_at": catalysts.get("fetched_at"),
                "row_count": sum(
                    len(catalysts.get(key) or [])
                    for key in ("earnings", "dividends", "news")
                ),
                "caveat": catalysts.get("caveat"),
                "data_gap": catalysts.get("data_gap"),
                "not_financial_advice": True,
            }
        )
        source_register.extend(catalysts.get("source_register") or [])

    unavailable = [
        row
        for row in source_register
        if str(row.get("source_status")) in {"unavailable", "missing-key", "provider-error"}
    ]
    delivered = {
        **workstation,
        "history": delivered_history,
        "chart_specs": (
            [
                *([chart_views["price"]] if chart_views["price"] else []),
                *list(chart_views["analysis"]),
            ]
            if delivery in {"chart", "chart-core", "technicals", "comparison"}
            else []
        ),
        "market_clock": clock,
        "chart_views": chart_views,
        "technical_analysis": technicals,
        "comparison": comparison,
        "financial_context": financial,
        "exact_news": news,
        "catalyst_context": catalysts,
        "crypto_derivatives": derivatives,
        "news": news.get("rows") or [],
        "selected_panels": [delivery],
        "panel_readiness": {
            panel: (
                "available"
                if panel == delivery
                else "available"
                if delivery in {"chart", "technicals"} and panel in {"trend", "momentum", "risk"}
                else "not-loaded"
            )
            for panel in ("summary", "chart", "trend", "momentum", "risk", "comparison", "financials", "news", "catalysts", "sources")
        },
        "source_register": source_register,
        "unavailable_sources": unavailable,
        "summary": {
            **workstation["summary"],
            "market_data_status": clock["market_data_status"],
            "market_data_as_of": clock["market_data_as_of"],
            "retrieved_at": clock["retrieved_at"],
            "fetched_at": clock["retrieved_at"],
            "delivery": delivery,
            "history_row_count": (
                len(history)
                if delivery in {"chart-core", "technicals"}
                else len(delivered_history)
            ),
            "technical_status": technicals.get("status"),
            "exact_news_count": len(news.get("rows") or []),
            "comparison_overlap_count": comparison.get("overlap_count", 0),
            "chart_type": chart_type,
        },
    }
    return delivered, unavailable


def build_symbol_delivery_contract(
    symbol: str,
    *,
    asset_class: str | None = None,
    interval: str = "1d",
    range_name: str = "3mo",
    runtime_mode: str = "cache",
    chart_type: str = "candlestick",
    delivery: str = "summary",
    compare: str | None = None,
    snapshot_base_dir: str | Path | None = None,
) -> dict[str, Any]:
    normalized_delivery = str(delivery or "summary").strip().lower()
    if normalized_delivery not in DELIVERY_PANELS:
        raise ValueError(f"Unsupported symbol delivery panel: {delivery}")
    normalized_chart = "line" if str(chart_type).lower() == "line" else "candlestick"
    normalized_runtime = (
        runtime_mode
        if runtime_mode in {"fixture", "cache", "live-if-available"}
        else "cache"
    )
    base_runtime = (
        normalized_runtime
        if normalized_delivery in {"chart", "chart-core", "technicals", "comparison"}
        else "fixture"
        if normalized_runtime == "fixture"
        else "cache"
    )
    base = build_symbol_workstation_contract(
        symbol,
        asset_class=asset_class,
        interval=interval,
        range_name=range_name,
        runtime_mode=base_runtime,
        snapshot_base_dir=snapshot_base_dir,
    )
    delivery_contract = {
        "version": SYMBOL_DELIVERY_VERSION,
        "requested_panel": normalized_delivery,
        "loaded_panels": [normalized_delivery],
        "provider_refresh_allowed": normalized_delivery
        in {"chart", "chart-core", "technicals", "financials", "news", "comparison"}
        and normalized_runtime == "live-if-available",
        "summary_provider_refresh": False,
        "identity_isolation": True,
        "shared_cache_partition": True,
        "broad_universe_rebuild": False,
    }
    if not base.get("workstations"):
        return {
            **base,
            "symbol_intelligence_version": SYMBOL_INTELLIGENCE_VERSION,
            "delivery": delivery_contract,
        }
    workstation, unavailable = _delivery_shell(
        base["workstations"][0],
        delivery=normalized_delivery,
        runtime_mode=normalized_runtime,
        chart_type=normalized_chart,
        compare=compare,
        snapshot_base_dir=snapshot_base_dir,
    )
    sources = list(workstation.get("source_register") or [])
    return {
        **base,
        "symbol_intelligence_version": SYMBOL_INTELLIGENCE_VERSION,
        "delivery": delivery_contract,
        "workstations": [workstation],
        "source_register": sources,
        "unavailable_sources": unavailable,
        "readiness": {
            **base.get("readiness", {}),
            "symbol_intelligence": True,
            "formula_version": FORMULA_VERSION,
            "delivery_version": SYMBOL_DELIVERY_VERSION,
            "loaded_panels": [normalized_delivery],
            "chart_type": normalized_chart,
        },
        "summary": {
            **workstation["summary"],
            "workspace": "symbol-workstation",
            "workstation_count": 1,
            "delivery": normalized_delivery,
        },
    }


def build_symbol_intelligence_contract(
    symbol: str,
    *,
    asset_class: str | None = None,
    interval: str = "1d",
    range_name: str = "3mo",
    runtime_mode: str = "fixture",
    chart_type: str = "candlestick",
    panels: str | list[str] | None = None,
    compare: str | None = None,
    snapshot_base_dir: str | Path | None = None,
) -> dict[str, Any]:
    normalized_chart = "line" if str(chart_type).lower() == "line" else "candlestick"
    selected_panels = normalize_panels(panels)
    compare_identity = (
        resolve_symbol(str(compare or ""), snapshot_base_dir=snapshot_base_dir)
        if compare
        else None
    )
    normalized_compare = compare_identity["symbol"] if compare_identity else None
    base = build_symbol_workstation_contract(
        symbol,
        asset_class=asset_class,
        interval=interval,
        range_name=range_name,
        runtime_mode=runtime_mode,
        snapshot_base_dir=snapshot_base_dir,
    )
    if not base.get("workstations"):
        return {**base, "symbol_intelligence_version": SYMBOL_INTELLIGENCE_VERSION}
    workstation = _enrich_workstation(
        base["workstations"][0],
        runtime_mode=runtime_mode,
        chart_type=normalized_chart,
        panels=selected_panels,
        compare=normalized_compare,
        snapshot_base_dir=snapshot_base_dir,
    )
    sources = workstation["source_register"]
    return {
        **base,
        "symbol_intelligence_version": SYMBOL_INTELLIGENCE_VERSION,
        "workstations": [workstation],
        "source_register": sources,
        "unavailable_sources": workstation["unavailable_sources"],
        "readiness": {
            **base.get("readiness", {}),
            "symbol_intelligence": True,
            "formula_version": FORMULA_VERSION,
            "selected_panels": selected_panels,
            "chart_type": normalized_chart,
        },
        "summary": {**workstation["summary"], "workspace": "symbol-workstation", "workstation_count": 1},
    }


def build_symbol_intelligence_fixture_catalog() -> dict[str, Any]:
    base = build_symbol_workstation_fixture_catalog()
    workstations = [
        _enrich_workstation(row, runtime_mode="fixture", chart_type="candlestick", panels=list(DEFAULT_PANELS), compare=None)
        for row in base.get("workstations", [])
    ]
    return {
        **base,
        "symbol_intelligence_version": SYMBOL_INTELLIGENCE_VERSION,
        "workstations": workstations,
        "readiness": {**base.get("readiness", {}), "symbol_intelligence": True, "formula_version": FORMULA_VERSION, "selected_panels": list(DEFAULT_PANELS), "chart_type": "candlestick"},
    }
