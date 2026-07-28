from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .data_contracts import DataGap


def _empty_frame():
    return pd.DataFrame() if pd is not None else []


def _frame(data: Any):
    if pd is None:
        return data if data is not None else []
    if data is None:
        return pd.DataFrame()
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], (list, tuple, dict, pd.DataFrame)):
            return _frame(data["data"])
        return pd.DataFrame([data])
    try:
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def _canonical(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def _normalize_common(data: Any, *, endpoint: str, required: list[str] | None = None, optional: list[str] | None = None, numeric: list[str] | None = None, date_columns: list[str] | None = None, symbol: str | None = None, source: str | None = None, is_proxy: bool = False, is_estimated: bool = False):
    frame = _frame(data)
    gaps: list[DataGap] = []
    if pd is None:
        return frame, [DataGap(field="pandas", reason="pandas is not installed.", severity="high", endpoint=endpoint, is_blocking=True)]
    if frame.empty:
        return frame, [DataGap(field=endpoint, reason="No rows returned.", severity="high", endpoint=endpoint, is_blocking=True)]
    if "date" not in {_canonical(col) for col in frame.columns} and getattr(frame, "index", None) is not None:
        try:
            if not isinstance(frame.index, pd.RangeIndex):
                frame = frame.reset_index().rename(columns={"index": "date"})
        except Exception:
            pass
    frame.columns = [_canonical(col) for col in frame.columns]
    rename = {
        "datetime": "date",
        "timestamp": "date",
        "symbol": "symbol",
        "ticker": "symbol",
        "adjclose": "adj_close",
        "adj_close": "adj_close",
        "regularmarketprice": "price",
        "marketcap": "market_cap",
        "market_capitalization": "market_cap",
        "totalrevenue": "revenue",
        "total_revenue": "revenue",
        "netincome": "net_income",
        "freecashflow": "free_cash_flow",
        "openinterest": "open_interest",
    }
    frame = frame.rename(columns={src: dst for src, dst in rename.items() if src in frame.columns})
    if symbol and "symbol" not in frame.columns:
        frame["symbol"] = str(symbol).upper()
    if "symbol" in frame.columns:
        frame["symbol"] = frame["symbol"].astype(str).str.upper()
    for date_col in date_columns or ["date", "period", "filing_date", "published_at", "expiration"]:
        if date_col in frame.columns:
            frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    for col in numeric or []:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in required or []:
        canonical = _canonical(col)
        if canonical not in frame.columns or frame[canonical].dropna().empty:
            gaps.append(DataGap(field=canonical, reason="Required field missing or empty after normalization.", severity="high", endpoint=endpoint, is_blocking=True))
    for col in optional or []:
        canonical = _canonical(col)
        if canonical not in frame.columns:
            gaps.append(DataGap(field=canonical, reason="Optional field unavailable.", severity="low", endpoint=endpoint, is_blocking=False))
    frame.attrs["endpoint"] = endpoint
    frame.attrs["source"] = source
    frame.attrs["is_proxy"] = bool(is_proxy)
    frame.attrs["is_estimated"] = bool(is_estimated)
    frame.attrs["data_gaps"] = [gap.to_dict() for gap in gaps]
    return frame, gaps


def normalize_price_history(data: Any, *, symbol: str | None = None, source: str | None = None, **_: Any):
    frame, gaps = _normalize_common(data, endpoint="price.history", required=["date", "close"], optional=["open", "high", "low", "adj_close", "volume"], numeric=["open", "high", "low", "close", "adj_close", "volume"], symbol=symbol, source=source)
    if pd is None or getattr(frame, "empty", True):
        return frame, gaps
    for col in ["open", "high", "low", "close", "adj_close", "volume"]:
        if col not in frame.columns:
            frame[col] = pd.NA
    if "adj_close" in frame.columns:
        frame["adj_close"] = frame["adj_close"].where(frame["adj_close"].notna(), frame.get("close"))
    return frame[[col for col in ["date", "symbol", "open", "high", "low", "close", "adj_close", "volume"] if col in frame.columns]], gaps


def normalize_quote_snapshot(data: Any, *, symbol: str | None = None, source: str | None = None, **_: Any):
    return _normalize_common(data, endpoint="price.quote", required=["symbol", "price"], optional=["daily_return", "volume", "currency", "exchange"], numeric=["price", "daily_return", "volume"], symbol=symbol, source=source)


def normalize_income_statement(data: Any, *, symbol: str | None = None, source: str | None = None, **_: Any):
    return _normalize_common(data, endpoint="equity.financials.income", required=["date"], optional=["revenue", "gross_profit", "operating_income", "net_income", "eps"], numeric=["revenue", "gross_profit", "operating_income", "net_income", "eps"], symbol=symbol, source=source)


def normalize_balance_sheet(data: Any, *, symbol: str | None = None, source: str | None = None, **_: Any):
    return _normalize_common(data, endpoint="equity.financials.balance", required=["date"], optional=["total_assets", "total_debt", "cash_and_equivalents", "shareholders_equity"], numeric=["total_assets", "total_debt", "cash_and_equivalents", "shareholders_equity"], symbol=symbol, source=source)


def normalize_cash_flow(data: Any, *, symbol: str | None = None, source: str | None = None, **_: Any):
    return _normalize_common(data, endpoint="equity.financials.cashflow", required=["date"], optional=["operating_cash_flow", "capital_expenditure", "free_cash_flow"], numeric=["operating_cash_flow", "capital_expenditure", "free_cash_flow"], symbol=symbol, source=source)


def normalize_ratios(data: Any, *, symbol: str | None = None, source: str | None = None, **_: Any):
    return _normalize_common(data, endpoint="equity.financials.ratios", required=["symbol"], optional=["pe", "pb", "ps", "roe", "roa", "debt_to_equity"], numeric=["pe", "pb", "ps", "roe", "roa", "debt_to_equity"], symbol=symbol, source=source, is_estimated=True)


def normalize_estimates(data: Any, *, symbol: str | None = None, source: str | None = None, **_: Any):
    return _normalize_common(data, endpoint="equity.estimates.eps", required=["symbol"], optional=["period", "eps_estimate", "revenue_estimate"], numeric=["eps_estimate", "revenue_estimate"], symbol=symbol, source=source)


def normalize_etf_holdings(data: Any, *, symbol: str | None = None, source: str | None = None, **_: Any):
    return _normalize_common(data, endpoint="etf.holdings", required=["symbol"], optional=["holding", "weight", "sector", "country"], numeric=["weight"], symbol=symbol, source=source)


def normalize_options_chain(data: Any, *, symbol: str | None = None, source: str | None = None, is_proxy: bool = False, **_: Any):
    return _normalize_common(data, endpoint="options.chain", required=["symbol"], optional=["expiration", "strike", "call_put", "open_interest", "volume", "iv"], numeric=["strike", "open_interest", "volume", "iv", "gamma"], symbol=symbol, source=source, is_proxy=is_proxy)


def normalize_macro_series(data: Any, *, series_id: str | None = None, source: str | None = None, **_: Any):
    frame, gaps = _normalize_common(data, endpoint="macro.fred_series", required=["date", "value"], optional=["series_id"], numeric=["value"], source=source)
    if pd is not None and not getattr(frame, "empty", True) and series_id and "series_id" not in frame.columns:
        frame["series_id"] = series_id
    return frame, gaps


def normalize_rates_curve(data: Any, *, source: str | None = None, is_proxy: bool = False, **_: Any):
    return _normalize_common(data, endpoint="rates.treasury_curve", required=["maturity", "rate"], optional=["date"], numeric=["rate"], source=source, is_proxy=is_proxy)


def normalize_energy_report(data: Any, *, source: str | None = None, is_proxy: bool = False, **_: Any):
    return _normalize_common(data, endpoint="energy.petroleum_status", required=[], optional=["date", "series", "value", "ticker", "latest_price"], numeric=["value", "latest_price", "daily_return"], source=source, is_proxy=is_proxy)


def normalize_shipping_data(data: Any, *, source: str | None = None, is_proxy: bool = True, **_: Any):
    return _normalize_common(data, endpoint="shipping.chokepoint_info", required=[], optional=["port", "chokepoint", "country", "region", "volume", "risk_score"], numeric=["lat", "lon", "volume", "risk_score"], source=source, is_proxy=is_proxy, is_estimated=is_proxy)


def normalize_technical_indicator(data: Any, *, symbol: str | None = None, indicator: str | None = None, source: str | None = None, **_: Any):
    frame, gaps = _normalize_common(data, endpoint=f"technical.{indicator or 'indicator'}", required=["date"], optional=["symbol", indicator or "value"], numeric=[indicator or "value"], symbol=symbol, source=source, is_estimated=True)
    if pd is not None and not getattr(frame, "empty", True) and indicator and "indicator" not in frame.columns:
        frame["indicator"] = indicator
    return frame, gaps


def normalize_news_events(data: Any, *, source: str | None = None, **_: Any):
    return _normalize_common(
        data,
        endpoint="news.world",
        required=["title"],
        optional=[
            "published_at",
            "source",
            "source_url",
            "provider",
            "fetched_at",
            "freshness",
            "source_status",
            "confidence",
            "coordinate_method",
            "country",
            "severity",
            "related_tickers",
            "data_gap",
            "caveat",
        ],
        source=source,
        is_proxy=True,
    )


def normalize_screener_rows(data: Any, *, source: str | None = None, **_: Any):
    frame, gaps = _normalize_common(data, endpoint="market.screener", required=["symbol"], optional=["name", "price", "market_cap", "sector", "return_1m_pct", "realized_volatility_pct", "valuation_score", "quality_score", "momentum_score", "risk_score"], numeric=["price", "market_cap", "return_1m_pct", "realized_volatility_pct", "valuation_score", "quality_score", "momentum_score", "risk_score"], source=source, is_estimated=True)
    if pd is not None and not getattr(frame, "empty", True) and "ticker" not in frame.columns and "symbol" in frame.columns:
        frame["ticker"] = frame["symbol"]
    return frame, gaps
