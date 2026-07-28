from __future__ import annotations

import os
from typing import Any

import pandas as pd

from .openbb_bridge import OPENBB_CAVEAT, get_openbb_version, is_openbb_installed


CATALOG_COLUMNS = [
    "app_area",
    "openbb_domain",
    "openbb_endpoint_label",
    "use_case",
    "provider_examples",
    "requires_key",
    "free_possible",
    "paid_likely",
    "native_fallback",
    "caveat",
]

OPENBB_ENV_VARS = [
    "FMP_API_KEY",
    "FRED_API_KEY",
    "EIA_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "FINNHUB_API_KEY",
    "POLYGON_API_KEY",
    "TIINGO_API_KEY",
    "TRADIER_API_KEY",
    "INTRINIO_API_KEY",
]


def _row(
    app_area: str,
    domain: str,
    endpoint: str,
    use_case: str,
    providers: str,
    *,
    requires_key: bool,
    free_possible: bool,
    paid_likely: bool,
    native_fallback: str,
    caveat: str,
) -> dict[str, Any]:
    return {
        "app_area": app_area,
        "openbb_domain": domain,
        "openbb_endpoint_label": endpoint,
        "use_case": use_case,
        "provider_examples": providers,
        "requires_key": requires_key,
        "free_possible": free_possible,
        "paid_likely": paid_likely,
        "native_fallback": native_fallback,
        "caveat": caveat,
    }


def build_openbb_capability_catalog() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    equity_endpoints = [
        ("profile", "Company identity, sector, listing, and description.", False, True),
        ("quote", "Latest quote and market snapshot.", False, True),
        ("historical", "Price history for charts and backtests.", False, True),
        ("screener", "Provider-backed equity candidate universe.", True, True),
        ("market snapshots", "Broad market snapshot tables.", True, True),
        ("gainers", "Market mover gainers table.", False, True),
        ("losers", "Market mover losers table.", False, True),
        ("active", "Most active equities table.", False, True),
        ("peers", "Peer comparison universe.", True, True),
        ("analyst consensus", "Provider-supplied consensus fields when licensed.", True, True),
        ("price target", "Provider-supplied price target fields when licensed.", True, True),
        ("income", "Reported income statement rows.", True, True),
        ("balance", "Reported balance sheet rows.", True, True),
        ("cash flow", "Reported cash flow rows.", True, True),
        ("ratios", "Reported or provider-derived ratios.", True, True),
        ("metrics", "Provider-derived financial metrics.", True, True),
        ("revenue per segment", "Reported segment revenue when available.", True, True),
        ("revenue per geography", "Reported geographic revenue when available.", True, True),
        ("filings", "SEC filing metadata.", False, True),
        ("transcripts", "Transcript metadata/content where licensed.", True, True),
        ("major holders", "Major holder table.", True, True),
        ("institutional ownership", "Institutional ownership table.", True, True),
        ("insider trading", "Insider activity table.", True, True),
        ("short interest", "Short interest table.", True, True),
        ("short volume", "Short volume table.", True, True),
        ("fails to deliver", "Fails-to-deliver records.", False, True),
    ]
    for endpoint, use_case, requires_key, paid_likely in equity_endpoints:
        rows.append(
            _row(
                "Financial Terminal / Screener",
                "Equity",
                endpoint,
                use_case,
                "OpenBB providers, yfinance, FMP, Finnhub, Polygon, Intrinio",
                requires_key=requires_key,
                free_possible=not paid_likely or endpoint in {"profile", "quote", "historical", "gainers", "losers", "active", "filings", "fails to deliver"},
                paid_likely=paid_likely,
                native_fallback="yfinance/fundamentals/screeners",
                caveat="Unavailable fields remain data gaps; estimates are shown only when provider-supplied.",
            )
        )

    etf_endpoints = ["search", "historical", "info", "holdings", "sectors", "countries", "performance", "gainers", "losers", "active"]
    for endpoint in etf_endpoints:
        rows.append(
            _row(
                "Screener / Portfolio Quant Lab",
                "ETF",
                endpoint,
                f"ETF {endpoint} coverage for exposures, holdings, and market mover context.",
                "OpenBB providers, yfinance, FMP",
                requires_key=endpoint in {"holdings", "sectors", "countries", "performance"},
                free_possible=endpoint in {"search", "historical", "info", "gainers", "losers", "active"},
                paid_likely=endpoint in {"holdings", "sectors", "countries", "performance"},
                native_fallback="yfinance/static ETF lists",
                caveat="ETF holdings and exposure coverage is provider-dependent.",
            )
        )

    rates_endpoints = ["treasury rates", "yield curve", "tips yields", "sofr", "effr", "iorb", "corporate spreads", "treasury auctions"]
    for endpoint in rates_endpoints:
        rows.append(
            _row(
                "Portfolio Quant Lab / Macro",
                "Fixed Income / Rates",
                endpoint,
                f"Rates context for factor exposure, cash proxy, and macro dashboarding.",
                "OpenBB providers, FRED, Treasury, FMP",
                requires_key=endpoint in {"corporate spreads"},
                free_possible=True,
                paid_likely=endpoint in {"corporate spreads"},
                native_fallback="FRED/rates/bond_data",
                caveat="Rate fields can be delayed or revised depending on source.",
            )
        )

    macro_endpoints = ["FRED series", "CPI", "unemployment", "PCE", "GDP", "calendar", "leading indicators", "FOMC documents", "country profile"]
    for endpoint in macro_endpoints:
        rows.append(
            _row(
                "Macro / AI Context",
                "Economy / Macro",
                endpoint,
                f"Macro time series or event context for research summaries.",
                "FRED, OpenBB providers, official public sources",
                requires_key=endpoint == "FRED series",
                free_possible=True,
                paid_likely=False,
                native_fallback="FRED/macro modules",
                caveat="Macro releases can be revised; AI context must include uncertainty.",
            )
        )

    commodity_endpoints = ["petroleum status report", "short-term energy outlook", "commodity spot", "weather bulletins if available"]
    for endpoint in commodity_endpoints:
        rows.append(
            _row(
                "Commodity / Energy",
                "Commodity / Energy",
                endpoint,
                "Energy and commodity context for market risk monitoring.",
                "EIA, OpenBB providers, official public sources",
                requires_key=endpoint in {"petroleum status report", "short-term energy outlook"},
                free_possible=True,
                paid_likely=False,
                native_fallback="EIA/energy_data/oil_flows",
                caveat="Weather and energy bulletins depend on provider availability.",
            )
        )

    derivatives_endpoints = ["options chains", "options surface", "unusual options", "futures curve", "futures historical"]
    for endpoint in derivatives_endpoints:
        rows.append(
            _row(
                "Financial Terminal / Portfolio Quant Lab",
                "Derivatives / Options",
                endpoint,
                "Options and futures context where official provider access exists.",
                "Tradier, Polygon, Intrinio, OpenBB providers",
                requires_key=True,
                free_possible=endpoint == "options chains",
                paid_likely=True,
                native_fallback="yfinance options/options_flow proxies",
                caveat="Options analytics are not trade directives and may require paid provider rights.",
            )
        )

    regulator_endpoints = ["SEC filings", "CFTC data", "CIK/symbol maps", "RSS litigation"]
    for endpoint in regulator_endpoints:
        rows.append(
            _row(
                "Financial Terminal / War Room",
                "Regulators",
                endpoint,
                "Regulatory context and identifiers for research workflows.",
                "SEC, CFTC, RSS, OpenBB providers",
                requires_key=False,
                free_possible=True,
                paid_likely=False,
                native_fallback="news_asset_linker/catalyst_graph",
                caveat="Regulatory documents require human verification before use.",
            )
        )

    technical_endpoints = ["RSI", "MACD", "ADX", "ATR", "Bollinger Bands", "Donchian", "Ichimoku", "VWAP", "relative rotation"]
    for endpoint in technical_endpoints:
        rows.append(
            _row(
                "Portfolio Quant Lab / Screener",
                "Technical",
                endpoint,
                "Technical indicator inputs for neutral factor research.",
                "OpenBB technical extensions, native technical_analysis",
                requires_key=False,
                free_possible=True,
                paid_likely=False,
                native_fallback="technical_analysis",
                caveat="Technical indicators are research features, not timing directives.",
            )
        )

    quant_endpoints = ["Sharpe", "Sortino", "Omega", "CAPM", "rolling statistics", "normality", "unit root", "summary stats"]
    for endpoint in quant_endpoints:
        rows.append(
            _row(
                "Portfolio Quant Lab",
                "Quantitative",
                endpoint,
                "Research statistics for strategy and portfolio evaluation.",
                "OpenBB quant extensions, native risk/portfolio modules",
                requires_key=False,
                free_possible=True,
                paid_likely=False,
                native_fallback="risk/portfolio_backtester/return_forecast",
                caveat="Backtest and forecast outputs are research estimates only.",
            )
        )
    return pd.DataFrame(rows, columns=CATALOG_COLUMNS)


def list_openbb_domains() -> list[str]:
    frame = build_openbb_capability_catalog()
    return sorted(frame["openbb_domain"].dropna().unique().tolist())


def list_openbb_targets_by_app_area(app_area: str | None = None) -> pd.DataFrame:
    frame = build_openbb_capability_catalog()
    if app_area:
        mask = frame["app_area"].str.contains(str(app_area), case=False, na=False)
        return frame[mask].reset_index(drop=True)
    return frame[["app_area", "openbb_domain", "openbb_endpoint_label", "use_case", "native_fallback", "caveat"]]


def list_openbb_required_keys() -> pd.DataFrame:
    rows = [
        {
            "env_var": env_var,
            "configured": bool(os.getenv(env_var)),
            "required_for_base_launch": False,
            "scope": "Optional OpenBB/provider enhancement",
            "caveat": "Secret value is not displayed. Verify provider terms and data rights.",
        }
        for env_var in OPENBB_ENV_VARS
    ]
    return pd.DataFrame(rows)


def openbb_endpoint_status_table() -> pd.DataFrame:
    frame = build_openbb_capability_catalog()
    installed = is_openbb_installed()
    frame = frame.copy()
    frame["openbb_installed"] = installed
    frame["openbb_version"] = get_openbb_version() if installed else None
    frame["backend_status"] = "installed_optional" if installed else "not_installed_optional"
    frame["key_status"] = frame["requires_key"].map(lambda value: "optional key may be required" if value else "no key expected for base check")
    frame["license_caveat"] = OPENBB_CAVEAT
    return frame


def openbb_app_mapping_table() -> pd.DataFrame:
    rows = [
        {"app_area": "Financial Terminal", "native_modules": "financial_terminal/fundamentals/yfinance", "openbb_targets": "profile, statements, ratios, metrics, estimates, filings, ownership", "source_mode": "Auto, Native only, OpenBB preferred, OpenBB only"},
        {"app_area": "Portfolio Quant Lab", "native_modules": "portfolio_backtester/alpha_library/risk", "openbb_targets": "price history, technical indicators, rates, macro series, ETF exposures", "source_mode": "Auto, Native only, OpenBB preferred, OpenBB only"},
        {"app_area": "Screener", "native_modules": "screeners/market_data/static universes", "openbb_targets": "equity screener, ETF screener, market movers, factor fields", "source_mode": "Auto, Native only, OpenBB preferred, OpenBB only"},
        {"app_area": "Provider Center / Data Quality", "native_modules": "provider_registry/provider_diagnostics/data_status", "openbb_targets": "installation, keys, capability catalog, button-triggered probes", "source_mode": "diagnostic only"},
        {"app_area": "AI analysis context", "native_modules": "ai_analysis/ai_prompts/ai_safety", "openbb_targets": "summarized enrichment only; no raw large frames", "source_mode": "button-triggered summaries"},
    ]
    return pd.DataFrame(rows)


def build_openbb_compatible_endpoint_catalog() -> pd.DataFrame:
    from .endpoint_catalog import endpoint_capability_table

    table = endpoint_capability_table()
    if isinstance(table, pd.DataFrame) and not table.empty:
        columns = [
            "endpoint_id",
            "app_area",
            "domain",
            "label",
            "native_providers",
            "openbb_candidate_paths",
            "optional_provider_keys",
            "estimated_allowed",
            "proxy_allowed",
            "caveat",
        ]
        return table[[column for column in columns if column in table.columns]]
    return pd.DataFrame()
