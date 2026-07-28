from __future__ import annotations

import re
from typing import Any

import pandas as pd


def _empty_frame(warning: str, *, provider: str = "openbb", source: str = "optional OpenBB backend") -> pd.DataFrame:
    frame = pd.DataFrame()
    frame.attrs["warning"] = warning
    frame.attrs["provider"] = provider
    frame.attrs["source"] = source
    return frame


def _to_frame(value: Any) -> pd.DataFrame:
    if value is None:
        return pd.DataFrame()
    if isinstance(value, pd.DataFrame):
        return value.copy()
    for method in ("to_df", "to_dataframe"):
        converter = getattr(value, method, None)
        if callable(converter):
            try:
                converted = converter()
                if isinstance(converted, pd.DataFrame):
                    return converted.copy()
            except Exception:
                pass
    if isinstance(value, dict):
        if "results" in value:
            return _to_frame(value["results"])
        if "data" in value and isinstance(value["data"], (list, tuple, dict)):
            return _to_frame(value["data"])
        return pd.DataFrame([value])
    if isinstance(value, (list, tuple)):
        return pd.DataFrame(list(value))
    return pd.DataFrame(value)


def _normalize_name(name: Any) -> str:
    text = str(name).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[^0-9A-Za-z]+", "_", text).strip("_").lower()
    return text


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    output.columns = [_normalize_name(col) for col in output.columns]
    return output


def _first_present(frame: pd.DataFrame, aliases: list[str]) -> str | None:
    normalized = {_normalize_name(alias) for alias in aliases}
    return next((col for col in frame.columns if col in normalized), None)


def _rename_aliases(frame: pd.DataFrame, aliases: dict[str, list[str]]) -> pd.DataFrame:
    output = frame.copy()
    rename = {}
    for target, candidates in aliases.items():
        matched = _first_present(output, candidates + [target])
        if matched and matched != target:
            rename[matched] = target
    return output.rename(columns=rename)


def _finish(frame: pd.DataFrame, *, provider: str, source: str, warning: str | None = None, is_estimate: bool = False) -> pd.DataFrame:
    output = frame.copy()
    output.attrs["provider"] = provider
    output.attrs["source"] = source
    if warning:
        output.attrs["warning"] = warning
    if is_estimate:
        output.attrs["is_estimate"] = True
    return output


def _require_any(frame: pd.DataFrame, required: list[str], warning: str, *, provider: str, source: str) -> pd.DataFrame:
    if frame.empty or not any(col in frame.columns and frame[col].notna().any() for col in required):
        return _empty_frame(warning, provider=provider, source=source)
    return _finish(frame, provider=provider, source=source)


def map_openbb_price_history(value: Any, *, provider: str = "openbb", source: str = "price history") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB price history returned no rows.", provider=provider, source=source)
    frame = _rename_aliases(
        frame,
        {
            "date": ["date", "datetime", "timestamp", "time"],
            "open": ["open"],
            "high": ["high"],
            "low": ["low"],
            "close": ["close", "last_price", "price"],
            "adj_close": ["adj_close", "adjusted_close", "adjclose"],
            "volume": ["volume"],
        },
    )
    if "date" not in frame.columns and not isinstance(frame.index, pd.RangeIndex):
        frame = frame.reset_index().rename(columns={frame.reset_index().columns[0]: "date"})
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    keep = [col for col in ["date", "open", "high", "low", "close", "adj_close", "volume"] if col in frame.columns]
    frame = frame[keep] if keep else frame
    return _require_any(frame, ["close", "adj_close"], "OpenBB price history lacks close fields.", provider=provider, source=source)


def map_openbb_equity_profile(value: Any, *, provider: str = "openbb", source: str = "equity profile") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB equity profile returned no rows.", provider=provider, source=source)
    frame = _rename_aliases(
        frame,
        {
            "ticker": ["symbol", "ticker"],
            "company_name": ["name", "company_name", "long_name", "short_name"],
            "sector": ["sector"],
            "industry": ["industry"],
            "country": ["country"],
            "exchange": ["exchange", "exchange_name"],
            "currency": ["currency"],
            "market_cap": ["market_cap", "marketcap", "mkt_cap"],
            "website": ["website", "homepage"],
            "description": ["description", "long_business_summary"],
        },
    )
    return _finish(frame, provider=provider, source=source)


def _map_statement(value: Any, *, provider: str, source: str, warning: str) -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame(warning, provider=provider, source=source)
    frame = _rename_aliases(frame, {"period": ["period", "date", "fiscal_date", "fiscal_period_ending"], "fiscal_year": ["fiscal_year", "year"]})
    if "period" in frame.columns:
        frame["period"] = pd.to_datetime(frame["period"], errors="ignore")
    return _finish(frame, provider=provider, source=source)


def map_openbb_income_statement(value: Any, *, provider: str = "openbb", source: str = "income statement") -> pd.DataFrame:
    frame = _map_statement(value, provider=provider, source=source, warning="OpenBB income statement returned no rows.")
    frame = _rename_aliases(frame, {"revenue": ["revenue", "total_revenue"], "net_income": ["net_income"], "eps": ["eps", "diluted_eps"]}) if not frame.empty else frame
    return frame


def map_openbb_balance_sheet(value: Any, *, provider: str = "openbb", source: str = "balance sheet") -> pd.DataFrame:
    frame = _map_statement(value, provider=provider, source=source, warning="OpenBB balance sheet returned no rows.")
    frame = _rename_aliases(frame, {"cash_and_equivalents": ["cash_and_equivalents", "cash"], "total_debt": ["total_debt"], "total_assets": ["total_assets"], "shareholders_equity": ["shareholders_equity", "total_equity"]}) if not frame.empty else frame
    return frame


def map_openbb_cash_flow(value: Any, *, provider: str = "openbb", source: str = "cash flow") -> pd.DataFrame:
    frame = _map_statement(value, provider=provider, source=source, warning="OpenBB cash flow returned no rows.")
    frame = _rename_aliases(frame, {"operating_cash_flow": ["operating_cash_flow"], "capital_expenditure": ["capital_expenditure", "capex"], "free_cash_flow": ["free_cash_flow"]}) if not frame.empty else frame
    return frame


def map_openbb_ratios(value: Any, *, provider: str = "openbb", source: str = "ratios") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB ratios returned no rows.", provider=provider, source=source)
    return _finish(_rename_aliases(frame, {"trailing_pe": ["trailing_pe", "pe_ratio"], "price_to_sales": ["price_to_sales", "ps_ratio"], "price_to_book": ["price_to_book", "pb_ratio"], "debt_to_equity": ["debt_to_equity"]}), provider=provider, source=source)


def map_openbb_metrics(value: Any, *, provider: str = "openbb", source: str = "metrics") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB metrics returned no rows.", provider=provider, source=source)
    return _finish(frame, provider=provider, source=source)


def map_openbb_estimates(value: Any, *, provider: str = "openbb", source: str = "estimates") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB estimates unavailable; estimates are not fabricated.", provider=provider, source=source)
    frame = _rename_aliases(frame, {"period": ["period", "date"], "eps_estimate": ["eps_estimate", "estimated_eps"], "revenue_estimate": ["revenue_estimate", "estimated_revenue"]})
    frame["is_estimate"] = True
    return _finish(frame, provider=provider, source=source, warning="Estimate fields are provider-supplied and labeled as estimates.", is_estimate=True)


def map_openbb_etf_holdings(value: Any, *, provider: str = "openbb", source: str = "ETF holdings") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB ETF holdings returned no rows.", provider=provider, source=source)
    frame = _rename_aliases(frame, {"ticker": ["symbol", "ticker", "holding_symbol"], "name": ["name", "holding_name"], "weight": ["weight", "weight_pct"], "sector": ["sector"], "country": ["country"]})
    return _finish(frame, provider=provider, source=source)


def map_openbb_etf_exposure(value: Any, *, provider: str = "openbb", source: str = "ETF exposure") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB ETF exposure returned no rows.", provider=provider, source=source)
    frame = _rename_aliases(frame, {"bucket": ["sector", "country", "category", "bucket", "name"], "weight": ["weight", "weight_pct", "exposure"]})
    return _finish(frame, provider=provider, source=source)


def map_openbb_options_chain(value: Any, *, provider: str = "openbb", source: str = "options chain") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB options chain returned no rows.", provider=provider, source=source)
    frame = _rename_aliases(frame, {"expiration": ["expiration", "expiry", "expiration_date"], "strike": ["strike"], "option_type": ["option_type", "type"], "open_interest": ["open_interest", "oi"], "implied_volatility": ["implied_volatility", "iv"]})
    return _finish(frame, provider=provider, source=source)


def map_openbb_treasury_rates(value: Any, *, provider: str = "openbb", source: str = "treasury rates") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB treasury rates returned no rows.", provider=provider, source=source)
    frame = _rename_aliases(frame, {"date": ["date"], "maturity": ["maturity", "tenor"], "rate": ["rate", "value", "yield"]})
    return _finish(frame, provider=provider, source=source)


def map_openbb_macro_series(value: Any, *, provider: str = "openbb", source: str = "macro series") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB macro series returned no rows.", provider=provider, source=source)
    frame = _rename_aliases(frame, {"date": ["date"], "value": ["value", "rate", "close"]})
    return _finish(frame, provider=provider, source=source, warning="Macro data may be revised after publication.")


def map_openbb_commodity_series(value: Any, *, provider: str = "openbb", source: str = "commodity series") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB commodity series returned no rows.", provider=provider, source=source)
    frame = _rename_aliases(frame, {"date": ["date"], "value": ["value", "price", "close"], "symbol": ["symbol", "ticker"]})
    return _finish(frame, provider=provider, source=source)


def map_openbb_news(value: Any, *, provider: str = "openbb", source: str = "news") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB news returned no rows.", provider=provider, source=source)
    frame = _rename_aliases(frame, {"published_at": ["published_at", "date", "datetime"], "title": ["title", "headline"], "url": ["url", "link"], "source_name": ["source", "source_name"]})
    return _finish(frame, provider=provider, source=source)


def map_openbb_filings(value: Any, *, provider: str = "openbb", source: str = "filings") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB filings returned no rows.", provider=provider, source=source)
    frame = _rename_aliases(frame, {"filing_date": ["filing_date", "date"], "form": ["form", "form_type"], "url": ["url", "link"], "description": ["description", "title"]})
    return _finish(frame, provider=provider, source=source)


def map_openbb_technical_indicators(value: Any, *, provider: str = "openbb", source: str = "technical indicators") -> pd.DataFrame:
    frame = _normalize_columns(_to_frame(value))
    if frame.empty:
        return _empty_frame("OpenBB technical indicators returned no rows.", provider=provider, source=source)
    return _finish(frame, provider=provider, source=source, warning="Technical indicators are neutral research features.")
