from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from .data_status import DataResult
from .openbb_bridge import OPENBB_CAVEAT, call_openbb_command_safe, openbb_to_dataresult
from .openbb_data_mapper import (
    map_openbb_balance_sheet,
    map_openbb_cash_flow,
    map_openbb_commodity_series,
    map_openbb_equity_profile,
    map_openbb_estimates,
    map_openbb_etf_exposure,
    map_openbb_etf_holdings,
    map_openbb_filings,
    map_openbb_income_statement,
    map_openbb_macro_series,
    map_openbb_metrics,
    map_openbb_options_chain,
    map_openbb_price_history,
    map_openbb_ratios,
    map_openbb_technical_indicators,
    map_openbb_treasury_rates,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame()


def _call(command: str, mapper: Callable[..., pd.DataFrame], *, requires_key: bool = False, **kwargs: Any) -> DataResult:
    return call_openbb_command_safe(command, mapper=lambda value: mapper(value, source=f"OpenBB {command}"), requires_key=requires_key, **kwargs)


def _generic(command: str, *, requires_key: bool = False, warning: str | None = None, **kwargs: Any) -> DataResult:
    result = call_openbb_command_safe(command, requires_key=requires_key, **kwargs)
    if warning and not result.warning:
        result.warning = warning
    return result


def _data_gap(command: str, message: str, *, requires_key: bool = False) -> DataResult:
    return openbb_to_dataresult(_frame(), command=command, error=message, warning=message, requires_key=requires_key, caveat=OPENBB_CAVEAT)


def get_openbb_company_profile(ticker: str) -> DataResult:
    return _call("equity.profile", map_openbb_equity_profile, symbol=ticker)


def get_openbb_price_history(ticker: str, start_date: Any = None, end_date: Any = None, interval: str = "1d") -> DataResult:
    kwargs = {"symbol": ticker, "interval": interval}
    if start_date is not None:
        kwargs["start_date"] = start_date
    if end_date is not None:
        kwargs["end_date"] = end_date
    return _call("equity.price.historical", map_openbb_price_history, **kwargs)


def get_openbb_income_statement(ticker: str, period: str = "annual") -> DataResult:
    return _call("equity.fundamental.income", map_openbb_income_statement, requires_key=True, symbol=ticker, period=period)


def get_openbb_balance_sheet(ticker: str, period: str = "annual") -> DataResult:
    return _call("equity.fundamental.balance", map_openbb_balance_sheet, requires_key=True, symbol=ticker, period=period)


def get_openbb_cash_flow(ticker: str, period: str = "annual") -> DataResult:
    return _call("equity.fundamental.cash", map_openbb_cash_flow, requires_key=True, symbol=ticker, period=period)


def get_openbb_ratios(ticker: str, period: str = "annual") -> DataResult:
    return _call("equity.fundamental.ratios", map_openbb_ratios, requires_key=True, symbol=ticker, period=period)


def get_openbb_metrics(ticker: str, period: str = "annual") -> DataResult:
    return _call("equity.fundamental.metrics", map_openbb_metrics, requires_key=True, symbol=ticker, period=period)


def get_openbb_estimates(ticker: str) -> DataResult:
    return _call("equity.estimates.consensus", map_openbb_estimates, requires_key=True, symbol=ticker)


def get_openbb_revenue_segments(ticker: str) -> DataResult:
    return _generic("equity.fundamental.revenue_per_segment", requires_key=True, symbol=ticker)


def get_openbb_revenue_geography(ticker: str) -> DataResult:
    return _generic("equity.fundamental.revenue_per_geography", requires_key=True, symbol=ticker)


def get_openbb_filings(ticker: str) -> DataResult:
    return _call("equity.fundamental.filings", map_openbb_filings, symbol=ticker)


def get_openbb_peers(ticker: str) -> DataResult:
    return _generic("equity.compare.peers", requires_key=True, symbol=ticker)


def get_openbb_ownership(ticker: str) -> DataResult:
    return _generic("equity.ownership.institutional", requires_key=True, symbol=ticker)


def get_openbb_etf_info(symbol: str) -> DataResult:
    return _generic("etf.info", symbol=symbol)


def get_openbb_etf_holdings(symbol: str) -> DataResult:
    return _call("etf.holdings", map_openbb_etf_holdings, requires_key=True, symbol=symbol)


def get_openbb_etf_sector_exposure(symbol: str) -> DataResult:
    return _call("etf.sectors", map_openbb_etf_exposure, requires_key=True, symbol=symbol)


def get_openbb_etf_country_exposure(symbol: str) -> DataResult:
    return _call("etf.countries", map_openbb_etf_exposure, requires_key=True, symbol=symbol)


def get_openbb_options_chain(ticker: str, expiry: str | None = None) -> DataResult:
    kwargs = {"symbol": ticker}
    if expiry:
        kwargs["expiration"] = expiry
    return _call("derivatives.options.chains", map_openbb_options_chain, requires_key=True, **kwargs)


def get_openbb_options_surface(ticker: str) -> DataResult:
    return _generic("derivatives.options.surface", requires_key=True, symbol=ticker)


def get_openbb_unusual_options(ticker: str) -> DataResult:
    return _generic("derivatives.options.unusual", requires_key=True, symbol=ticker)


def get_openbb_treasury_rates() -> DataResult:
    return _call("fixedincome.government.treasury_rates", map_openbb_treasury_rates)


def get_openbb_yield_curve() -> DataResult:
    return _call("fixedincome.government.yield_curve", map_openbb_treasury_rates)


def get_openbb_fred_series(series_id: str) -> DataResult:
    return _call("economy.fred_series", map_openbb_macro_series, requires_key=True, symbol=series_id)


def get_openbb_macro_calendar() -> DataResult:
    return _call("economy.calendar", map_openbb_macro_series)


def get_openbb_petroleum_status_report() -> DataResult:
    return _call("commodity.energy.petroleum_status_report", map_openbb_commodity_series, requires_key=True)


def get_openbb_energy_outlook() -> DataResult:
    return _call("commodity.energy.short_term_energy_outlook", map_openbb_commodity_series, requires_key=True)


def get_openbb_commodity_spot(symbol_or_category: str) -> DataResult:
    return _call("commodity.spot", map_openbb_commodity_series, symbol=symbol_or_category)


def get_openbb_technical_indicators(ticker: str, indicators: list[str]) -> DataResult:
    rows: list[pd.DataFrame] = []
    errors: list[str] = []
    for indicator in indicators:
        normalized = str(indicator).strip().lower().replace(" ", "_")
        result = _call(f"technical.{normalized}", map_openbb_technical_indicators, symbol=ticker)
        if result.ok and isinstance(result.data, pd.DataFrame):
            frame = result.data.copy()
            frame["indicator"] = normalized
            rows.append(frame)
        elif result.error:
            errors.append(f"{normalized}: {result.error}")
    if not rows:
        return _data_gap("technical.indicators", "; ".join(errors) or "No OpenBB technical indicators returned usable rows.")
    combined = pd.concat(rows, ignore_index=True)
    warning = "; ".join(errors[:4]) if errors else None
    return openbb_to_dataresult(combined, command="technical.indicators", warning=warning)


def get_openbb_equity_screener(filters: dict[str, Any] | None = None) -> DataResult:
    return _generic("equity.discovery.screener", requires_key=True, **(filters or {}))


def get_openbb_equity_gainers() -> DataResult:
    return _generic("equity.discovery.gainers")


def get_openbb_equity_losers() -> DataResult:
    return _generic("equity.discovery.losers")


def get_openbb_equity_active() -> DataResult:
    return _generic("equity.discovery.active")


def get_openbb_etf_gainers() -> DataResult:
    return _generic("etf.discovery.gainers")


def get_openbb_etf_losers() -> DataResult:
    return _generic("etf.discovery.losers")


def get_openbb_etf_active() -> DataResult:
    return _generic("etf.discovery.active")
