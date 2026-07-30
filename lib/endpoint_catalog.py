from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .data_contracts import DataRequest, EndpointCapability


def _cap(
    endpoint_id: str,
    app_area: str,
    domain: str,
    label: str,
    description: str,
    *,
    required_fields: list[str] | None = None,
    optional_fields: list[str] | None = None,
    native_providers: list[str] | None = None,
    openbb_candidate_paths: list[str] | None = None,
    optional_provider_keys: list[str] | None = None,
    estimated_allowed: bool = False,
    proxy_allowed: bool = False,
    caveat: str = "",
    downstream_pages: list[str] | None = None,
) -> EndpointCapability:
    return EndpointCapability(
        endpoint_id=endpoint_id,
        app_area=app_area,
        domain=domain,
        label=label,
        description=description,
        required_fields=required_fields or [],
        optional_fields=optional_fields or [],
        native_providers=native_providers or [],
        openbb_candidate_paths=openbb_candidate_paths or [],
        optional_provider_keys=optional_provider_keys or [],
        estimated_allowed=estimated_allowed,
        proxy_allowed=proxy_allowed,
        caveat=caveat,
        downstream_pages=downstream_pages or [],
    )


def build_internal_endpoint_catalog() -> dict[str, EndpointCapability]:
    rows: list[EndpointCapability] = []
    base_pages = {
        "market": ["Market Pulse", "Screener", "Portfolio Quant Lab"],
        "equity": ["Financial Terminal", "Screener"],
        "etf": ["ETF Analyzer", "Screener", "Portfolio Quant Lab"],
        "options": ["Financial Terminal", "Portfolio Quant Lab"],
        "macro": ["Macro", "Scenario Lab", "War Room"],
        "rates": ["Macro", "Portfolio Quant Lab", "Scenario Lab"],
        "commodity": ["Energy Geopolitics", "Scenario Lab"],
        "energy": ["Energy Geopolitics", "War Room", "Scenario Lab"],
        "shipping": ["Energy Geopolitics", "War Room"],
        "crypto": ["Crypto Intelligence", "Screener"],
        "technical": ["Portfolio Quant Lab", "Screener"],
        "quant": ["Portfolio Quant Lab"],
        "news": ["News", "War Room"],
        "osint": ["War Room", "Scenario Lab"],
        "natural": ["War Room", "Data Provider Center"],
    }

    market_specs = [
        ("price.history", "Price History", ["date", "open", "high", "low", "close"], ["adj_close", "volume"], ["yfinance"], ["equity.price.historical", "index.price.historical", "crypto.price.historical"], False, False),
        ("price.quote", "Quote", ["symbol", "price"], ["volume", "currency", "exchange"], ["yfinance"], ["equity.price.quote", "crypto.price.quote"], False, False),
        ("price.snapshot", "Price Snapshot", ["symbol", "price"], ["daily_return", "volume"], ["yfinance"], ["equity.price.quote", "equity.discovery.active"], False, False),
        ("market.movers", "Market Movers", ["symbol"], ["price", "change_percent"], ["screeners"], ["equity.discovery.gainers", "equity.discovery.losers", "equity.discovery.active"], False, False),
        ("market.index_constituents", "Index Constituents", ["ticker"], ["name", "sector", "market_cap"], ["static"], ["index.constituents"], False, True),
    ]
    for endpoint, label, required, optional, native, openbb, estimated, proxy in market_specs:
        rows.append(_cap(endpoint, "Market", "market", label, f"{label} endpoint for market views.", required_fields=required, optional_fields=optional, native_providers=native, openbb_candidate_paths=openbb, estimated_allowed=estimated, proxy_allowed=proxy, downstream_pages=base_pages["market"]))

    equity_specs = [
        ("equity.profile", "Company Profile", ["symbol"], ["name", "sector", "industry", "market_cap"], ["yfinance", "fundamentals"], ["equity.profile"], [], False, False),
        ("equity.financials.income", "Income Statement", ["date"], ["revenue", "operating_income", "net_income", "eps"], ["fundamentals"], ["equity.fundamental.income", "equity.fundamental.income_statement", "equity.fundamental.financials.income"], ["FMP_API_KEY", "INTRINIO_API_KEY"], False, False),
        ("equity.financials.balance", "Balance Sheet", ["date"], ["assets", "liabilities", "equity", "debt"], ["fundamentals"], ["equity.fundamental.balance", "equity.fundamental.balance_sheet", "equity.fundamental.financials.balance"], ["FMP_API_KEY", "INTRINIO_API_KEY"], False, False),
        ("equity.financials.cashflow", "Cash Flow", ["date"], ["operating_cash_flow", "free_cash_flow", "capex"], ["fundamentals"], ["equity.fundamental.cash", "equity.fundamental.cash_flow", "equity.fundamental.cashflow"], ["FMP_API_KEY", "INTRINIO_API_KEY"], False, False),
        ("equity.financials.ratios", "Ratios", ["symbol"], ["pe", "pb", "roe", "debt_to_equity"], ["fundamentals"], ["equity.fundamental.ratios", "equity.fundamental.financial_ratios"], ["FMP_API_KEY"], True, False),
        ("equity.financials.metrics", "Metrics", ["symbol"], ["market_cap", "enterprise_value", "ev_ebitda"], ["fundamentals"], ["equity.fundamental.metrics", "equity.fundamental.key_metrics"], ["FMP_API_KEY"], True, False),
        ("equity.estimates.eps", "EPS Estimates", ["symbol"], ["period", "eps_estimate"], [], ["equity.estimates.consensus", "equity.estimates.forward_eps", "equity.calendar.earnings"], ["FMP_API_KEY", "FINNHUB_API_KEY"], False, False),
        ("equity.estimates.revenue", "Revenue Estimates", ["symbol"], ["period", "revenue_estimate"], [], ["equity.estimates.consensus", "equity.estimates.forward_sales"], ["FMP_API_KEY", "FINNHUB_API_KEY"], False, False),
        ("equity.earnings.calendar", "Earnings Calendar", ["symbol"], ["date", "eps_estimate", "eps_actual"], ["financial_terminal"], ["equity.calendar.earnings", "economy.calendar"], [], False, False),
        ("equity.revenue.segments", "Revenue Segments", ["symbol"], ["segment", "revenue"], [], ["equity.fundamental.revenue_per_segment"], ["FMP_API_KEY"], False, False),
        ("equity.revenue.geography", "Revenue Geography", ["symbol"], ["geography", "revenue"], [], ["equity.fundamental.revenue_per_geography"], ["FMP_API_KEY"], False, False),
        ("equity.filings", "Filings", ["symbol"], ["filing_date", "form", "url"], ["news_asset_linker"], ["equity.fundamental.filings", "regulators.sec.filings"], [], False, False),
        ("equity.ownership", "Ownership", ["symbol"], ["holder", "shares"], [], ["equity.ownership.institutional", "equity.ownership.major_holders"], ["FMP_API_KEY"], False, False),
        ("equity.peers", "Peers", ["symbol"], ["peer"], ["etf_peers"], ["equity.compare.peers"], ["FMP_API_KEY"], True, True),
        ("equity.news", "Company News", ["symbol"], ["title", "published_at", "source"], ["news"], ["news.company"], [], False, True),
    ]
    for endpoint, label, required, optional, native, openbb, keys, estimated, proxy in equity_specs:
        rows.append(_cap(endpoint, "Financial Terminal", "equity", label, f"{label} endpoint for company research.", required_fields=required, optional_fields=optional, native_providers=native, openbb_candidate_paths=openbb, optional_provider_keys=keys, estimated_allowed=estimated, proxy_allowed=proxy, caveat="Unavailable company fields remain visible data gaps.", downstream_pages=base_pages["equity"]))

    etf_specs = [
        ("etf.profile", "ETF Profile", ["symbol"], ["name", "expense_ratio", "aum"], ["yfinance"], ["etf.info"], [], False, False),
        ("etf.holdings", "ETF Holdings", ["symbol"], ["holding", "weight"], [], ["etf.holdings"], ["FMP_API_KEY"], False, False),
        ("etf.sectors", "ETF Sectors", ["symbol"], ["sector", "weight"], ["static"], ["etf.sectors"], ["FMP_API_KEY"], True, True),
        ("etf.countries", "ETF Countries", ["symbol"], ["country", "weight"], ["static"], ["etf.countries"], ["FMP_API_KEY"], True, True),
        ("etf.performance", "ETF Performance", ["symbol"], ["return_1m", "return_ytd"], ["screeners"], ["etf.performance"], [], False, True),
        ("etf.exposure", "ETF Exposure", ["symbol"], ["exposure_type", "weight"], ["static"], ["etf.holdings", "etf.sectors", "etf.countries"], ["FMP_API_KEY"], True, True),
    ]
    for endpoint, label, required, optional, native, openbb, keys, estimated, proxy in etf_specs:
        rows.append(_cap(endpoint, "ETF / Screener", "etf", label, f"{label} endpoint for ETF research.", required_fields=required, optional_fields=optional, native_providers=native, openbb_candidate_paths=openbb, optional_provider_keys=keys, estimated_allowed=estimated, proxy_allowed=proxy, downstream_pages=base_pages["etf"]))

    derivative_specs = [
        ("options.chain", "Options Chain", ["symbol"], ["expiration", "strike", "call_put", "open_interest", "volume", "iv"], ["yfinance"], ["derivatives.options.chains", "derivatives.options.chain", "equity.options.chains"], ["TRADIER_API_KEY", "POLYGON_API_KEY"], False, False),
        ("options.surface", "Options Surface", ["symbol"], ["expiration", "strike", "iv"], [], ["derivatives.options.surface"], ["TRADIER_API_KEY", "POLYGON_API_KEY"], False, False),
        ("options.unusual", "Unusual Options", ["symbol"], ["volume", "open_interest"], ["options_flow"], ["derivatives.options.unusual"], ["TRADIER_API_KEY", "POLYGON_API_KEY"], True, True),
        ("options.gamma_proxy", "Gamma Proxy", ["symbol"], ["gamma_exposure"], ["options_flow"], ["derivatives.options.chains"], ["TRADIER_API_KEY"], True, True),
        ("futures.curve", "Futures Curve", ["symbol"], ["expiry", "price"], [], ["derivatives.futures.curve"], ["FMP_API_KEY"], False, False),
        ("futures.historical", "Futures Historical", ["symbol"], ["date", "close"], ["yfinance"], ["derivatives.futures.historical"], ["FMP_API_KEY"], False, True),
    ]
    for endpoint, label, required, optional, native, openbb, keys, estimated, proxy in derivative_specs:
        rows.append(_cap(endpoint, "Options / Derivatives", "options", label, f"{label} endpoint for derivatives research.", required_fields=required, optional_fields=optional, native_providers=native, openbb_candidate_paths=openbb, optional_provider_keys=keys, estimated_allowed=estimated, proxy_allowed=proxy, caveat="Options and gamma fields are labeled proxy/estimated unless provider-supplied.", downstream_pages=base_pages["options"]))

    macro_specs = [
        ("macro.fred_series", "FRED Series", ["date", "value"], ["series_id"], ["macro"], ["economy.fred_series"], ["FRED_API_KEY"], False, False),
        ("macro.calendar", "Macro Calendar", ["date"], ["event", "actual", "consensus"], ["macro"], ["economy.calendar"], [], False, False),
        ("macro.cpi", "CPI", ["date", "value"], ["series_id"], ["macro"], ["economy.cpi", "economy.fred_series"], ["FRED_API_KEY"], False, False),
        ("macro.pce", "PCE", ["date", "value"], ["series_id"], ["macro"], ["economy.pce", "economy.fred_series"], ["FRED_API_KEY"], False, False),
        ("macro.unemployment", "Unemployment", ["date", "value"], ["series_id"], ["macro"], ["economy.unemployment", "economy.fred_series"], ["FRED_API_KEY"], False, False),
        ("macro.gdp", "GDP", ["date", "value"], ["series_id"], ["macro"], ["economy.gdp", "economy.fred_series"], ["FRED_API_KEY"], False, False),
        ("rates.treasury_curve", "Treasury Curve", ["maturity", "rate"], ["date"], ["rates"], ["fixedincome.government.yield_curve", "fixedincome.government.treasury_rates"], [], False, True),
        ("rates.treasury_rates", "Treasury Rates", ["maturity", "rate"], ["date"], ["rates"], ["fixedincome.government.treasury_rates"], [], False, True),
        ("rates.sofr", "SOFR", ["date", "value"], [], ["rates"], ["fixedincome.rates.sofr"], [], False, False),
        ("rates.effr", "EFFR", ["date", "value"], [], ["rates"], ["fixedincome.rates.effr"], [], False, False),
        ("rates.credit_spreads", "Credit Spreads", ["date", "value"], [], ["rates"], ["fixedincome.credit.spreads", "economy.fred_series"], ["FRED_API_KEY"], True, True),
    ]
    for endpoint, label, required, optional, native, openbb, keys, estimated, proxy in macro_specs:
        domain = "rates" if endpoint.startswith("rates.") else "macro"
        rows.append(_cap(endpoint, "Macro / Rates", domain, label, f"{label} endpoint for macro and rates dashboards.", required_fields=required, optional_fields=optional, native_providers=native, openbb_candidate_paths=openbb, optional_provider_keys=keys, estimated_allowed=estimated, proxy_allowed=proxy, caveat="Macro/rates data may be delayed or revised; proxies are labeled.", downstream_pages=base_pages[domain]))

    energy_specs = [
        ("commodity.spot", "Commodity Spot", ["symbol", "price"], ["date"], ["energy_data", "yfinance"], ["commodity.spot"], [], False, True),
        ("energy.petroleum_status", "Petroleum Status", ["date"], ["inventory", "production", "imports", "exports"], ["energy_data"], ["commodity.energy.petroleum_status_report", "commodity.petroleum_status_report"], ["EIA_API_KEY"], False, False),
        ("energy.short_term_outlook", "Short-Term Energy Outlook", ["date"], ["forecast", "scenario"], ["energy_data"], ["commodity.energy.short_term_energy_outlook"], ["EIA_API_KEY"], False, False),
        ("energy.inventory", "Inventory", ["date", "value"], ["series"], ["energy_data"], ["commodity.energy.inventory", "commodity.energy.petroleum_status_report"], ["EIA_API_KEY"], False, False),
        ("energy.production", "Production", ["date", "value"], ["series"], ["energy_data"], ["commodity.energy.production"], ["EIA_API_KEY"], False, False),
        ("energy.refinery", "Refinery", ["date", "value"], ["series"], ["energy_data"], ["commodity.energy.refinery"], ["EIA_API_KEY"], False, False),
        ("energy.import_export", "Import/Export", ["date", "value"], ["series"], ["energy_data"], ["commodity.energy.import_export"], ["EIA_API_KEY"], False, False),
        ("shipping.port_info", "Port Info", ["port"], ["country", "lat", "lon"], ["static"], ["shipping.port_info"], [], True, True),
        ("shipping.port_volume", "Port Volume", ["port"], ["volume"], [], ["shipping.port_volume"], ["FMP_API_KEY"], False, True),
        ("shipping.chokepoint_info", "Chokepoint Info", ["chokepoint"], ["region", "related_assets"], ["static"], ["shipping.chokepoint_info"], [], True, True),
        ("shipping.chokepoint_volume", "Chokepoint Volume", ["chokepoint"], ["volume"], [], ["shipping.chokepoint_volume"], ["FMP_API_KEY"], False, True),
    ]
    for endpoint, label, required, optional, native, openbb, keys, estimated, proxy in energy_specs:
        domain = "shipping" if endpoint.startswith("shipping.") else "energy" if endpoint.startswith("energy.") else "commodity"
        rows.append(_cap(endpoint, "Energy / Shipping", domain, label, f"{label} endpoint for energy and chokepoint monitoring.", required_fields=required, optional_fields=optional, native_providers=native, openbb_candidate_paths=openbb, optional_provider_keys=keys, estimated_allowed=estimated, proxy_allowed=proxy, caveat="No live AIS is claimed unless an explicit provider is configured.", downstream_pages=base_pages[domain]))

    crypto_specs = [
        ("crypto.price", "Crypto Price", ["symbol", "price"], ["volume"], ["coingecko", "yfinance"], ["crypto.price.quote"], [], False, False),
        ("crypto.ohlcv", "Crypto OHLCV", ["date", "open", "high", "low", "close"], ["volume"], ["binance", "coingecko", "yfinance"], ["crypto.price.historical"], [], False, False),
        ("crypto.open_interest", "Open Interest", ["symbol", "open_interest"], ["date"], ["binance"], ["crypto.derivatives.open_interest"], [], False, False),
        ("crypto.funding", "Funding", ["symbol", "funding_rate"], ["date"], ["binance"], ["crypto.derivatives.funding"], [], False, False),
        ("crypto.taker_ratio", "Taker Ratio", ["symbol", "taker_ratio"], ["date"], ["binance"], ["crypto.derivatives.taker_ratio"], [], False, False),
        ("crypto.long_short", "Long/Short", ["symbol", "long_short_ratio"], ["date"], ["binance"], ["crypto.derivatives.long_short"], [], False, False),
        ("crypto.liquidation_pressure", "Liquidation Pressure", ["symbol"], ["pressure_score"], ["crypto_derivatives"], ["crypto.derivatives.liquidations"], [], True, True),
        ("crypto.defillama_tvl", "DeFiLlama TVL", ["protocol", "tvl"], ["date"], ["defillama"], ["crypto.defi.tvl"], [], False, False),
        ("crypto.stablecoins", "Stablecoins", ["symbol", "market_cap"], ["chain"], ["defillama", "coingecko"], ["crypto.defi.stablecoins"], [], False, False),
    ]
    for endpoint, label, required, optional, native, openbb, keys, estimated, proxy in crypto_specs:
        rows.append(_cap(endpoint, "Crypto Intelligence", "crypto", label, f"{label} endpoint for crypto intelligence.", required_fields=required, optional_fields=optional, native_providers=native, openbb_candidate_paths=openbb, optional_provider_keys=keys, estimated_allowed=estimated, proxy_allowed=proxy, downstream_pages=base_pages["crypto"]))

    technical_specs = ["rsi", "macd", "adx", "atr", "bbands", "donchian", "ichimoku", "vwap"]
    for item in technical_specs:
        rows.append(_cap(f"technical.{item}", "Portfolio Quant Lab", "technical", item.upper(), f"{item.upper()} technical indicator.", required_fields=["date", "symbol"], optional_fields=[item], native_providers=["technical_analysis"], openbb_candidate_paths=[f"technical.{item}"], estimated_allowed=True, proxy_allowed=True, caveat="Technical indicators are research features, not timing directives.", downstream_pages=base_pages["technical"]))

    quant_specs = ["sharpe", "sortino", "omega", "capm", "rolling_stats", "drawdown", "var_cvar", "correlation"]
    for item in quant_specs:
        rows.append(_cap(f"quant.{item}", "Portfolio Quant Lab", "quant", item.replace("_", " ").title(), f"{item} quantitative research statistic.", required_fields=["returns"], optional_fields=[], native_providers=["risk", "portfolio_backtester"], openbb_candidate_paths=[f"quant.{item}"], estimated_allowed=True, proxy_allowed=False, caveat="Quant outputs are historical research statistics.", downstream_pages=base_pages["quant"]))

    news_specs = [
        ("news.rss", "RSS News", ["title"], ["published_at", "source"], ["news"], ["news.rss"], [], False, True),
        ("news.gdelt", "GDELT News", ["title"], ["published_at", "source", "country"], ["geopolitical_news"], ["news.gdelt"], [], False, True),
        ("news.company", "Company News", ["symbol", "title"], ["published_at", "source"], ["news_asset_linker"], ["news.company"], [], False, True),
        ("news.world", "World News", ["title"], ["country", "domain"], ["geopolitical_news"], ["news.world"], [], False, True),
        ("osint.events", "OSINT Events", ["title", "severity"], ["lat", "lon", "country"], ["event_stream"], ["osint.events"], [], True, True),
        ("natural.earthquakes", "Earthquakes", ["title", "severity"], ["lat", "lon", "magnitude"], ["usgs_earthquake"], [], [], False, False),
        ("natural.eonet_events", "Natural Events", ["event_id", "title", "severity"], ["lat", "lon", "category_ids", "source_url"], ["nasa_eonet"], [], [], False, False),
        ("osint.source_freshness", "Source Freshness", ["source", "status"], ["age_minutes"], ["source_freshness"], ["osint.source_freshness"], [], True, True),
    ]
    for endpoint, label, required, optional, native, openbb, keys, estimated, proxy in news_specs:
        domain = "osint" if endpoint.startswith("osint.") else "natural" if endpoint.startswith("natural.") else "news"
        rows.append(_cap(endpoint, "News / OSINT", domain, label, f"{label} endpoint for news and OSINT workflows.", required_fields=required, optional_fields=optional, native_providers=native, openbb_candidate_paths=openbb, optional_provider_keys=keys, estimated_allowed=estimated, proxy_allowed=proxy, caveat="OSINT events require source verification and may include heuristic severity.", downstream_pages=base_pages[domain]))

    return {item.endpoint_id: item for item in rows}


def list_endpoint_domains() -> list[str]:
    return sorted({item.domain for item in build_internal_endpoint_catalog().values()})


def list_endpoints_by_app_area(app_area: str | None = None) -> list[dict[str, Any]]:
    catalog = build_internal_endpoint_catalog()
    rows = [item.to_dict() for item in catalog.values()]
    if app_area:
        text = str(app_area).lower()
        rows = [row for row in rows if text in str(row.get("app_area", "")).lower() or any(text in str(page).lower() for page in row.get("downstream_pages", []))]
    return rows


def get_endpoint_definition(endpoint_id: str) -> EndpointCapability | None:
    return build_internal_endpoint_catalog().get(endpoint_id)


def endpoint_required_fields(endpoint_id: str) -> list[str]:
    definition = get_endpoint_definition(endpoint_id)
    return list(definition.required_fields) if definition else []


def endpoint_optional_fields(endpoint_id: str) -> list[str]:
    definition = get_endpoint_definition(endpoint_id)
    return list(definition.optional_fields) if definition else []


def endpoint_native_fallbacks(endpoint_id: str) -> list[str]:
    definition = get_endpoint_definition(endpoint_id)
    return list(definition.native_providers) if definition else []


def endpoint_openbb_candidates(endpoint_id: str) -> list[str]:
    definition = get_endpoint_definition(endpoint_id)
    return list(definition.openbb_candidate_paths) if definition else []


def endpoint_capability_table():
    rows = [item.to_dict() for item in build_internal_endpoint_catalog().values()]
    return pd.DataFrame(rows) if pd is not None else rows


def validate_endpoint_request(request: DataRequest | dict[str, Any]) -> tuple[bool, list[str]]:
    req = request if isinstance(request, DataRequest) else DataRequest(**request)
    issues: list[str] = []
    definition = get_endpoint_definition(req.endpoint)
    if definition is None:
        return False, [f"Unknown endpoint: {req.endpoint}"]
    if req.source_mode == "openbb_only" and not definition.openbb_candidate_paths:
        issues.append(f"{req.endpoint} has no OpenBB candidate path in the internal catalog.")
    if req.source_mode == "native_only" and not definition.native_providers:
        issues.append(f"{req.endpoint} has no native provider fallback in the internal catalog.")
    needs_symbol = any(field in {"symbol", "ticker"} for field in definition.required_fields)
    if needs_symbol and not req.symbol and not req.symbols:
        issues.append(f"{req.endpoint} requires a symbol or symbols.")
    if not req.allow_proxy and definition.proxy_allowed and req.source_mode == "provider_specific" and req.provider_preference == "proxy":
        issues.append("Proxy data was requested but allow_proxy is false.")
    return not issues, issues
