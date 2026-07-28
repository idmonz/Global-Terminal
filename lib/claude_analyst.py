from __future__ import annotations

from .ai_analysis import (
    analyze_crypto_neutral,
    analyze_energy_geopolitical_neutral,
    analyze_etf_neutral as _analyze_etf_response,
    analyze_overview_neutral,
    analyze_portfolio_risk_neutral,
    analyze_stock_neutral as _analyze_stock_response,
    summarize_cross_asset_scenarios_neutral,
)


def _text(response) -> str:
    return getattr(response, "text", str(response))


def summarize_scenarios_neutral(scenarios) -> str:
    return _text(summarize_cross_asset_scenarios_neutral({"scenarios": scenarios}))


def analyze_stock_neutral(*args, **kwargs) -> str:
    return _text(_analyze_stock_response({"args": args, "kwargs": kwargs}))


def analyze_etf_neutral(*args, **kwargs) -> str:
    return _text(_analyze_etf_response({"args": args, "kwargs": kwargs}))


def analyze_crypto_market_neutral(*args, **kwargs) -> str:
    return _text(analyze_crypto_neutral({"args": args, "kwargs": kwargs}))


def summarize_crypto_scenarios_neutral(*args, **kwargs) -> str:
    text = args[0] if args else kwargs.get("scenarios")
    return _text(analyze_crypto_neutral({"scenario_rows": text}))


def analyze_oil_geopolitical_neutral(*args, **kwargs) -> str:
    return _text(analyze_energy_geopolitical_neutral({"args": args, "kwargs": kwargs}))


def analyze_macro_neutral(*args, **kwargs) -> str:
    return _text(analyze_overview_neutral({"args": args, "kwargs": kwargs}))


def analyze_portfolio_neutral(*args, **kwargs) -> str:
    return _text(analyze_portfolio_risk_neutral({"args": args, "kwargs": kwargs}))
