from __future__ import annotations

from typing import Any, Callable

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .data_contracts import DataGap, DataRequest, UnifiedDataResult
from .data_freshness_engine import compute_data_freshness
from .data_gap_engine import detect_data_gaps
from .data_status import DataResult, error_result, ok_result
from .endpoint_catalog import get_endpoint_definition, validate_endpoint_request
from .provider_router import provider_missing_key_gaps, resolve_provider_route
from .schema_normalizer import (
    normalize_balance_sheet,
    normalize_cash_flow,
    normalize_energy_report,
    normalize_estimates,
    normalize_etf_holdings,
    normalize_income_statement,
    normalize_macro_series,
    normalize_news_events,
    normalize_options_chain,
    normalize_price_history,
    normalize_quote_snapshot,
    normalize_rates_curve,
    normalize_ratios,
    normalize_screener_rows,
    normalize_shipping_data,
    normalize_technical_indicator,
)
from .source_priority import source_confidence_score


def _empty_frame():
    return pd.DataFrame() if pd is not None else []


def _result_data(result: DataResult) -> Any:
    return getattr(result, "data", None)


def _normalizer_for(endpoint: str) -> Callable[..., tuple[Any, list[DataGap]]]:
    mapping: dict[str, Callable[..., tuple[Any, list[DataGap]]]] = {
        "price.history": normalize_price_history,
        "price.quote": normalize_quote_snapshot,
        "price.snapshot": normalize_quote_snapshot,
        "equity.financials.income": normalize_income_statement,
        "equity.financials.balance": normalize_balance_sheet,
        "equity.financials.cashflow": normalize_cash_flow,
        "equity.financials.ratios": normalize_ratios,
        "equity.financials.metrics": normalize_ratios,
        "equity.estimates.eps": normalize_estimates,
        "equity.estimates.revenue": normalize_estimates,
        "etf.holdings": normalize_etf_holdings,
        "options.chain": normalize_options_chain,
        "options.gamma_proxy": normalize_options_chain,
        "macro.fred_series": normalize_macro_series,
        "macro.cpi": normalize_macro_series,
        "macro.pce": normalize_macro_series,
        "macro.unemployment": normalize_macro_series,
        "macro.gdp": normalize_macro_series,
        "rates.treasury_curve": normalize_rates_curve,
        "rates.treasury_rates": normalize_rates_curve,
        "rates.sofr": normalize_macro_series,
        "rates.effr": normalize_macro_series,
        "rates.credit_spreads": normalize_macro_series,
        "commodity.spot": normalize_energy_report,
        "energy.petroleum_status": normalize_energy_report,
        "energy.short_term_outlook": normalize_energy_report,
        "energy.inventory": normalize_energy_report,
        "energy.production": normalize_energy_report,
        "energy.refinery": normalize_energy_report,
        "energy.import_export": normalize_energy_report,
        "shipping.port_info": normalize_shipping_data,
        "shipping.port_volume": normalize_shipping_data,
        "shipping.chokepoint_info": normalize_shipping_data,
        "shipping.chokepoint_volume": normalize_shipping_data,
        "news.rss": normalize_news_events,
        "news.gdelt": normalize_news_events,
        "news.company": normalize_news_events,
        "news.world": normalize_news_events,
        "osint.events": normalize_news_events,
        "natural.earthquakes": normalize_news_events,
        "osint.source_freshness": normalize_screener_rows,
    }
    if endpoint.startswith("technical."):
        return normalize_technical_indicator
    if endpoint.startswith("crypto."):
        return normalize_price_history if endpoint in {"crypto.price", "crypto.ohlcv"} else normalize_screener_rows
    return mapping.get(endpoint, normalize_screener_rows)


def _unified_from_status(
    request: DataRequest,
    status: DataResult,
    *,
    data: Any = None,
    gaps: list[DataGap] | None = None,
    native_used: bool = False,
    openbb_used: bool = False,
    fallback_used: bool = False,
    is_proxy: bool = False,
    caveats: list[str] | None = None,
) -> UnifiedDataResult:
    definition = get_endpoint_definition(request.endpoint)
    all_gaps = list(gaps or [])
    all_gaps.extend(detect_data_gaps(data, definition.required_fields if definition else [], endpoint=request.endpoint, provider=status.provider))
    all_gaps.extend(provider_missing_key_gaps(request.endpoint, status.provider) if openbb_used else [])
    freshness = status.refreshed_status() if hasattr(status, "refreshed_status") else compute_data_freshness(ok=status.ok).get("status", "unknown")
    warnings = [item for item in [status.warning] if item]
    errors = [item for item in [status.error] if item]
    metadata = {
        "request": request.to_dict(),
        "status": status.to_dict() if hasattr(status, "to_dict") else {},
        "source_confidence": source_confidence_score(ok=status.ok, freshness=freshness, gaps=len(all_gaps), is_proxy=is_proxy, is_estimated=bool(status.is_estimated)),
    }
    return UnifiedDataResult(
        ok=bool(status.ok) and not any(gap.is_blocking for gap in all_gaps if gap.severity == "high" and request.required_fields),
        data=data,
        provider=status.provider,
        source=status.source,
        endpoint=request.endpoint,
        native_used=native_used,
        openbb_used=openbb_used,
        fallback_used=fallback_used,
        is_estimated=bool(status.is_estimated),
        is_proxy=bool(is_proxy),
        freshness=freshness,
        data_gaps=all_gaps,
        warnings=warnings,
        errors=errors,
        caveats=[item for item in (caveats or []) if item],
        metadata=metadata,
    )


def _normalize_result(request: DataRequest, status: DataResult, *, native_used: bool = False, openbb_used: bool = False, fallback_used: bool = False, is_proxy: bool = False) -> UnifiedDataResult:
    normalizer = _normalizer_for(request.endpoint)
    kwargs = {"source": status.source}
    if request.symbol:
        kwargs["symbol"] = request.symbol
    if request.endpoint.startswith("technical."):
        kwargs["indicator"] = request.endpoint.split(".", 1)[1]
    if request.endpoint.startswith("macro.") or request.endpoint.startswith("rates."):
        kwargs["series_id"] = request.user_params.get("series_id") or request.symbol
    if request.endpoint.startswith("options."):
        kwargs["is_proxy"] = is_proxy
    if request.endpoint.startswith("energy.") or request.endpoint.startswith("commodity.") or request.endpoint.startswith("shipping."):
        kwargs["is_proxy"] = is_proxy
    data, gaps = normalizer(_result_data(status), **kwargs)
    definition = get_endpoint_definition(request.endpoint)
    caveats = [definition.caveat] if definition else []
    return _unified_from_status(request, status, data=data, gaps=gaps, native_used=native_used, openbb_used=openbb_used, fallback_used=fallback_used, is_proxy=is_proxy, caveats=caveats)


def _data_gap_result(request: DataRequest, reason: str) -> UnifiedDataResult:
    status = error_result(source=request.endpoint, provider="data_gap", error=reason, data=_empty_frame(), coverage="unavailable")
    return _unified_from_status(request, status, data=_empty_frame(), gaps=[DataGap(field=request.endpoint, reason=reason, severity="high", endpoint=request.endpoint, is_blocking=True)])


def _call_openbb(request: DataRequest, route_provider: str = "openbb") -> UnifiedDataResult:
    from . import openbb_provider_adapter as adapter

    symbol = request.symbol or (request.symbols[0] if request.symbols else "")
    period = request.period or "annual"
    endpoint = request.endpoint
    calls: dict[str, Callable[[], DataResult]] = {
        "price.history": lambda: adapter.get_openbb_price_history(symbol, start_date=request.start_date, end_date=request.end_date, interval=request.interval or "1d"),
        "equity.profile": lambda: adapter.get_openbb_company_profile(symbol),
        "equity.financials.income": lambda: adapter.get_openbb_income_statement(symbol, period=period),
        "equity.financials.balance": lambda: adapter.get_openbb_balance_sheet(symbol, period=period),
        "equity.financials.cashflow": lambda: adapter.get_openbb_cash_flow(symbol, period=period),
        "equity.financials.ratios": lambda: adapter.get_openbb_ratios(symbol, period=period),
        "equity.financials.metrics": lambda: adapter.get_openbb_metrics(symbol, period=period),
        "equity.estimates.eps": lambda: adapter.get_openbb_estimates(symbol),
        "equity.estimates.revenue": lambda: adapter.get_openbb_estimates(symbol),
        "equity.revenue.segments": lambda: adapter.get_openbb_revenue_segments(symbol),
        "equity.revenue.geography": lambda: adapter.get_openbb_revenue_geography(symbol),
        "equity.filings": lambda: adapter.get_openbb_filings(symbol),
        "equity.peers": lambda: adapter.get_openbb_peers(symbol),
        "equity.ownership": lambda: adapter.get_openbb_ownership(symbol),
        "etf.profile": lambda: adapter.get_openbb_etf_info(symbol),
        "etf.holdings": lambda: adapter.get_openbb_etf_holdings(symbol),
        "etf.sectors": lambda: adapter.get_openbb_etf_sector_exposure(symbol),
        "etf.countries": lambda: adapter.get_openbb_etf_country_exposure(symbol),
        "options.chain": lambda: adapter.get_openbb_options_chain(symbol, expiry=request.user_params.get("expiry")),
        "options.surface": lambda: adapter.get_openbb_options_surface(symbol),
        "options.unusual": lambda: adapter.get_openbb_unusual_options(symbol),
        "rates.treasury_curve": adapter.get_openbb_yield_curve,
        "rates.treasury_rates": adapter.get_openbb_treasury_rates,
        "macro.fred_series": lambda: adapter.get_openbb_fred_series(request.user_params.get("series_id") or symbol),
        "macro.calendar": adapter.get_openbb_macro_calendar,
        "energy.petroleum_status": adapter.get_openbb_petroleum_status_report,
        "energy.short_term_outlook": adapter.get_openbb_energy_outlook,
        "commodity.spot": lambda: adapter.get_openbb_commodity_spot(symbol or request.user_params.get("category", "oil")),
    }
    call = calls.get(endpoint)
    if call is None and endpoint.startswith("technical."):
        call = lambda: adapter.get_openbb_technical_indicators(symbol, [endpoint.split(".", 1)[1]])
    if call is None:
        return _data_gap_result(request, f"OpenBB route is cataloged but no adapter function is implemented for {endpoint}.")
    status = call()
    return _normalize_result(request, status, openbb_used=True)


def _call_native(request: DataRequest) -> UnifiedDataResult:
    symbol = request.symbol or (request.symbols[0] if request.symbols else "")
    endpoint = request.endpoint
    try:
        if endpoint == "price.history":
            from .market_data import fetch_price_history

            data, status = fetch_price_history(symbol, period=request.period or "1y", interval=request.interval or "1d")
            return _normalize_result(request, status, native_used=True)
        if endpoint in {"price.quote", "price.snapshot"}:
            from .market_data import latest_price_snapshot

            data, status = latest_price_snapshot(request.symbols or [symbol])
            status.data = data
            return _normalize_result(request, status, native_used=True)
        if endpoint.startswith("equity.financials."):
            from .fundamentals import get_balance_sheet, get_cash_flow, get_income_statement, get_key_ratios

            if endpoint.endswith(".income"):
                data, status = get_income_statement(symbol, period=request.period or "annual")
            elif endpoint.endswith(".balance"):
                data, status = get_balance_sheet(symbol, period=request.period or "annual")
            elif endpoint.endswith(".cashflow"):
                data, status = get_cash_flow(symbol, period=request.period or "annual")
            else:
                data, status = get_key_ratios(symbol)
            status.data = data
            return _normalize_result(request, status, native_used=True, is_proxy=endpoint.endswith((".ratios", ".metrics")))
        if endpoint in {"equity.profile"}:
            from .financial_terminal import build_company_header

            data, status, _ = build_company_header(symbol)
            status.data = data
            return _normalize_result(request, status, native_used=True)
        if endpoint in {"equity.estimates.eps", "equity.estimates.revenue", "equity.earnings.calendar"}:
            from .financial_terminal import build_earnings_panel

            data, status, _ = build_earnings_panel(symbol)
            status.data = data.get("earnings_history") if isinstance(data, dict) else data
            return _normalize_result(request, status, native_used=True)
        if endpoint.startswith("macro."):
            from .macro import get_macro_dashboard

            data, status = get_macro_dashboard()
            status.data = data
            return _normalize_result(request, status, native_used=True, is_proxy=True)
        if endpoint.startswith("rates."):
            from .rates import get_rates_snapshot

            data, status = get_rates_snapshot()
            status.data = data
            return _normalize_result(request, status, native_used=True, is_proxy=True)
        if endpoint.startswith("energy.") or endpoint == "commodity.spot":
            from .energy_data import build_energy_fundamentals_dashboard, get_yfinance_energy_fallback

            if endpoint == "commodity.spot":
                data, status = get_yfinance_energy_fallback(period=request.period or "6mo")
            else:
                datasets, status = build_energy_fundamentals_dashboard(enable_eia=True)
                data = datasets.get("yfinance_fallback", _empty_frame()) if endpoint in {"energy.petroleum_status", "energy.short_term_outlook"} else next((value for value in datasets.values() if value is not None), _empty_frame())
            status.data = data
            return _normalize_result(request, status, native_used=True, is_proxy=not status.ok or status.provider == "yfinance")
        if endpoint.startswith("shipping."):
            rows = [
                {"chokepoint": "Strait of Hormuz", "region": "Middle East", "related_assets": ["CL=F", "BZ=F", "USO"], "source_status": "static metadata / proxy"},
                {"chokepoint": "Suez Canal", "region": "Egypt", "related_assets": ["shipping", "oil"], "source_status": "static metadata / proxy"},
                {"chokepoint": "Bab el-Mandeb", "region": "Red Sea", "related_assets": ["oil", "shipping"], "source_status": "static metadata / proxy"},
            ]
            data = pd.DataFrame(rows) if pd is not None else rows
            status = ok_result(data, source="static chokepoint registry", provider="static", is_estimated=True, warning="Static metadata / proxy only. No live AIS is claimed.")
            return _normalize_result(request, status, native_used=True, is_proxy=True)
        if endpoint.startswith("technical."):
            from .market_data import fetch_price_history

            data, status = fetch_price_history(symbol, period=request.period or "1y", interval=request.interval or "1d")
            status.data = data
            return _normalize_result(request, status, native_used=True, is_proxy=True)
        if endpoint.startswith("crypto."):
            from .market_data import fetch_price_history

            data, status = fetch_price_history(symbol or "BTC-USD", period=request.period or "1y", interval=request.interval or "1d")
            status.data = data
            return _normalize_result(request, status, native_used=True, is_proxy=endpoint not in {"crypto.price", "crypto.ohlcv"})
        if endpoint in {"market.movers", "market.index_constituents"} or endpoint.startswith("etf.") or endpoint.startswith("osint.source_freshness"):
            from .screeners import build_screener_with_source_mode

            data, status, _ = build_screener_with_source_mode("Stocks", period=request.period or "1y", source_mode="Native only")
            status.data = data
            return _normalize_result(request, status, native_used=True, is_proxy=endpoint != "market.movers")
        if endpoint in {"news.rss", "news.gdelt", "news.world"}:
            from .live_feeds import fetch_gdelt_feed, fetch_live_news_feed, fetch_rss_feed

            query = request.user_params.get("query") or "geopolitical risk OR oil OR macro"
            if endpoint == "news.rss":
                data, status = fetch_rss_feed()
            elif endpoint == "news.gdelt":
                data, status = fetch_gdelt_feed(query=query)
            else:
                data, status = fetch_live_news_feed(query=query)
            status.data = data
            return _normalize_result(request, status, native_used=True, is_proxy=not status.ok)
        if endpoint == "natural.earthquakes":
            from .live_feeds import fetch_usgs_earthquakes

            data, status = fetch_usgs_earthquakes()
            status.data = data
            return _normalize_result(request, status, native_used=True, is_proxy=False)
        if endpoint == "osint.events":
            from .event_stream import build_event_stream
            from .live_feeds import build_keyless_runtime_feeds

            payload = build_keyless_runtime_feeds(query=request.user_params.get("query") or "geopolitical risk OR oil OR earthquake OR crypto")
            data = build_event_stream(news=payload.get("news"), crypto=payload.get("crypto"), natural=payload.get("natural"))
            status = ok_result(
                data,
                source="keyless OSINT runtime",
                provider="live_feeds",
                warning="; ".join(payload.get("data_gaps", [])[:4]) or None,
                coverage=f"{len(data)} events",
                is_estimated=False,
            )
            return _normalize_result(request, status, native_used=True, is_proxy=False)
    except Exception as exc:
        return _data_gap_result(request, f"Native route failed for {endpoint}: {exc}")
    return _data_gap_result(request, f"No native adapter implemented for {endpoint}.")


def request_data(request: DataRequest | dict[str, Any], **overrides: Any) -> UnifiedDataResult:
    req = request if isinstance(request, DataRequest) else DataRequest(**request)
    for key, value in overrides.items():
        setattr(req, key, value)
    valid, issues = validate_endpoint_request(req)
    if not valid:
        return _data_gap_result(req, "; ".join(issues))
    route = resolve_provider_route(req)
    if route.openbb:
        result = _call_openbb(req)
        if result.ok or req.source_mode == "openbb_only" or not req.allow_fallback:
            result.metadata["route"] = route.to_dict()
            return result
        fallback = _call_native(req)
        fallback.fallback_used = True
        fallback.warnings.extend(result.warnings or ["OpenBB route unavailable; native fallback used."])
        fallback.metadata["route"] = route.to_dict()
        fallback.metadata["openbb_attempt"] = result.to_dict()
        return fallback
    if route.provider == "data_gap":
        return _data_gap_result(req, route.warning or "No provider route available.")
    result = _call_native(req)
    result.metadata["route"] = route.to_dict()
    return result


def _request(endpoint: str, *, symbol: str | None = None, symbols: list[str] | None = None, app_area: str = "", source_mode: str = "auto", **kwargs: Any) -> UnifiedDataResult:
    definition = get_endpoint_definition(endpoint)
    required_fields = kwargs.pop("required_fields", definition.required_fields if definition else [])
    optional_fields = kwargs.pop("optional_fields", definition.optional_fields if definition else [])
    allow_proxy = kwargs.pop("allow_proxy", bool(definition.proxy_allowed) if definition else False)
    allow_estimates = kwargs.pop("allow_estimates", bool(definition.estimated_allowed) if definition else False)
    return request_data(
        DataRequest(
            app_area=app_area or (definition.app_area if definition else ""),
            domain=definition.domain if definition else "",
            endpoint=endpoint,
            symbol=symbol,
            symbols=symbols or ([] if symbol is None else [symbol]),
            source_mode=source_mode,
            required_fields=required_fields,
            optional_fields=optional_fields,
            allow_proxy=allow_proxy,
            allow_estimates=allow_estimates,
            **kwargs,
        )
    )


def request_price_history(symbol: str, **kwargs: Any) -> UnifiedDataResult:
    return _request("price.history", symbol=symbol, app_area="Portfolio Quant Lab", **kwargs)


def request_financials(symbol: str, statement: str = "income", **kwargs: Any) -> UnifiedDataResult:
    endpoint = {"income": "equity.financials.income", "balance": "equity.financials.balance", "cashflow": "equity.financials.cashflow", "ratios": "equity.financials.ratios", "metrics": "equity.financials.metrics"}.get(statement, statement)
    return _request(endpoint, symbol=symbol, app_area="Financial Terminal", **kwargs)


def request_macro_series(series_id: str, **kwargs: Any) -> UnifiedDataResult:
    params = dict(kwargs.pop("user_params", {}) or {})
    params["series_id"] = series_id
    return _request("macro.fred_series", symbol=series_id, app_area="Macro", user_params=params, **kwargs)


def request_rates_curve(**kwargs: Any) -> UnifiedDataResult:
    return _request("rates.treasury_curve", app_area="Macro", **kwargs)


def request_energy_data(endpoint: str = "energy.petroleum_status", **kwargs: Any) -> UnifiedDataResult:
    return _request(endpoint, app_area="Energy Geopolitics", **kwargs)


def request_shipping_data(endpoint: str = "shipping.chokepoint_info", **kwargs: Any) -> UnifiedDataResult:
    return _request(endpoint, app_area="War Room", **kwargs)


def request_options_chain(symbol: str, **kwargs: Any) -> UnifiedDataResult:
    return _request("options.chain", symbol=symbol, app_area="Financial Terminal", **kwargs)


def request_screener_data(asset_class: str = "Stocks", **kwargs: Any) -> UnifiedDataResult:
    params = dict(kwargs.pop("user_params", {}) or {})
    params["asset_class"] = asset_class
    return _request("market.movers", app_area="Screener", user_params=params, **kwargs)


def request_technical_indicator(symbol: str, indicator: str = "rsi", **kwargs: Any) -> UnifiedDataResult:
    return _request(f"technical.{indicator}", symbol=symbol, app_area="Portfolio Quant Lab", **kwargs)


def request_crypto_data(symbol: str = "BTC-USD", endpoint: str = "crypto.ohlcv", **kwargs: Any) -> UnifiedDataResult:
    return _request(endpoint, symbol=symbol, app_area="Crypto Intelligence", **kwargs)


def request_news_events(**kwargs: Any) -> UnifiedDataResult:
    return _request("osint.events", app_area="War Room", **kwargs)
