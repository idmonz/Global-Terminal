from __future__ import annotations

from typing import Any

from .tradingview_widget_embed import build_tradingview_market_quotes_embed, build_tradingview_widget_disclaimer


def build_watchlist_tradingview_disclaimer() -> dict[str, str]:
    return build_tradingview_widget_disclaimer()


def build_watchlist_market_quotes_widget(symbols: list[str] | None = None, *, enabled: bool = False) -> dict[str, Any]:
    symbol = (symbols or ["SPY"])[0] if symbols else "SPY"
    payload = build_tradingview_market_quotes_embed(enabled=enabled, symbol=symbol)
    payload["symbols"] = symbols or []
    return payload


def build_watchlist_symbol_chart_widget(symbol: str = "SPY", *, enabled: bool = False) -> dict[str, Any]:
    payload = build_tradingview_market_quotes_embed(enabled=enabled, symbol=symbol)
    payload["kind"] = "symbol_chart"
    return payload


def build_watchlist_ticker_tape_widget(symbols: list[str] | None = None, *, enabled: bool = False) -> dict[str, Any]:
    return {"enabled": enabled, "kind": "ticker_tape", "symbols": symbols or [], "html": "" if not enabled else "<div class='tradingview-widget' data-kind='ticker_tape'></div>", "disclaimer": build_watchlist_tradingview_disclaimer(), "status": "external_optional" if enabled else "disabled"}

