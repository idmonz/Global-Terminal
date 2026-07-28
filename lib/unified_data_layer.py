from __future__ import annotations

from typing import Any

from .data_router import (
    request_data as _request_data,
    request_crypto_data,
    request_energy_data,
    request_financials,
    request_macro_series,
    request_news_events,
    request_options_chain,
    request_price_history,
    request_rates_curve,
    request_screener_data,
    request_shipping_data,
    request_technical_indicator,
)


def request_data(*args: Any, **kwargs: Any):
    return _request_data(*args, **kwargs)


def get_unified_price_history(symbol: str, **kwargs: Any):
    return request_price_history(symbol, **kwargs)


def get_unified_financials(symbol: str, statement: str = "income", **kwargs: Any):
    return request_financials(symbol, statement=statement, **kwargs)


def get_unified_screener(asset_class: str = "Stocks", **kwargs: Any):
    return request_screener_data(asset_class=asset_class, **kwargs)


def get_unified_portfolio_inputs(symbols: list[str], **kwargs: Any) -> dict[str, Any]:
    price_results = {symbol: get_unified_price_history(symbol, app_area="Portfolio Quant Lab", **kwargs) for symbol in symbols}
    coverage = sum(1 for result in price_results.values() if result.ok)
    return {
        "symbols": symbols,
        "price_history": price_results,
        "coverage_pct": round(coverage / max(1, len(symbols)) * 100, 1),
        "source_confidence": round(sum(result.metadata.get("source_confidence", 0) for result in price_results.values()) / max(1, len(price_results)), 1),
        "data_gaps": [gap for result in price_results.values() for gap in result.data_gaps],
        "caveat": "Portfolio inputs are research data only and may include missing assets or proxy-labeled fields.",
    }


def get_unified_macro_dashboard_data(**kwargs: Any) -> dict[str, Any]:
    series = {
        "cpi": request_macro_series("CPIAUCSL", **kwargs),
        "unemployment": request_macro_series("UNRATE", **kwargs),
        "gdp": request_macro_series("GDP", **kwargs),
    }
    rates = request_rates_curve(**kwargs)
    return {
        "macro_series": series,
        "rates_curve": rates,
        "data_gaps": [gap for result in list(series.values()) + [rates] for gap in result.data_gaps],
        "source_confidence": round(sum(result.metadata.get("source_confidence", 0) for result in list(series.values()) + [rates]) / 4, 1),
    }


def get_unified_energy_dashboard_data(**kwargs: Any) -> dict[str, Any]:
    petroleum = request_energy_data("energy.petroleum_status", **kwargs)
    outlook = request_energy_data("energy.short_term_outlook", **kwargs)
    spot = request_energy_data("commodity.spot", **kwargs)
    shipping = request_shipping_data("shipping.chokepoint_info", **kwargs)
    results = [petroleum, outlook, spot, shipping]
    return {
        "petroleum_status": petroleum,
        "short_term_outlook": outlook,
        "commodity_spot": spot,
        "shipping_chokepoints": shipping,
        "data_gaps": [gap for result in results for gap in result.data_gaps],
        "source_confidence": round(sum(result.metadata.get("source_confidence", 0) for result in results) / len(results), 1),
    }


def get_unified_war_room_data(**kwargs: Any) -> dict[str, Any]:
    events = request_news_events(**kwargs)
    rates = request_rates_curve(**kwargs)
    energy = request_energy_data("energy.petroleum_status", **kwargs)
    chokepoints = request_shipping_data("shipping.chokepoint_info", **kwargs)
    return {
        "events": events,
        "rates": rates,
        "energy": energy,
        "chokepoints": chokepoints,
        "rail_cards": [
            {"label": "Macro/Rates", "result": rates},
            {"label": "Energy", "result": energy},
            {"label": "Chokepoints", "result": chokepoints},
        ],
        "data_gaps": [gap for result in [events, rates, energy, chokepoints] for gap in result.data_gaps],
    }


def get_unified_options_data(symbol: str, **kwargs: Any):
    return request_options_chain(symbol, **kwargs)


def get_unified_ai_context_data(symbol: str | None = None, symbols: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
    symbols = symbols or ([symbol] if symbol else ["SPY"])
    portfolio = get_unified_portfolio_inputs(symbols, **kwargs)
    macro = get_unified_macro_dashboard_data(**kwargs)
    energy = get_unified_energy_dashboard_data(**kwargs)
    return {
        "symbols": symbols,
        "portfolio": portfolio,
        "macro": macro,
        "energy": energy,
        "caveats": [
            "AI context packets are summarized and button-triggered only.",
            "No output is financial advice or a prediction.",
        ],
        "source_confidence": round((portfolio["source_confidence"] + macro["source_confidence"] + energy["source_confidence"]) / 3, 1),
    }


def get_unified_technical_bundle(symbol: str, indicators: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
    indicators = indicators or ["rsi", "macd", "atr"]
    results = {indicator: request_technical_indicator(symbol, indicator=indicator, **kwargs) for indicator in indicators}
    return {"symbol": symbol.upper(), "indicators": results, "data_gaps": [gap for result in results.values() for gap in result.data_gaps]}


def get_unified_crypto_bundle(symbol: str = "BTC-USD", **kwargs: Any) -> dict[str, Any]:
    return {
        "ohlcv": request_crypto_data(symbol=symbol, endpoint="crypto.ohlcv", **kwargs),
        "funding": request_crypto_data(symbol=symbol, endpoint="crypto.funding", **kwargs),
        "open_interest": request_crypto_data(symbol=symbol, endpoint="crypto.open_interest", **kwargs),
    }
