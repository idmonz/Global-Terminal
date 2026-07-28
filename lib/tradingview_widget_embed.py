from __future__ import annotations

import html
from typing import Any


def build_tradingview_widget_disclaimer() -> dict[str, str]:
    return {
        "label": "External visual supplement",
        "text": "TradingView widgets are optional visual supplements only. They are not used for calculations, backtests, recommendations, provider health, or data-quality claims.",
    }


def _widget_payload(kind: str, *, enabled: bool = False, symbol: str = "SPY", width: str = "100%", height: int = 420) -> dict[str, Any]:
    disclaimer = build_tradingview_widget_disclaimer()
    if not enabled:
        return {"enabled": False, "kind": kind, "html": "", "disclaimer": disclaimer, "status": "disabled"}
    safe_symbol = html.escape(str(symbol or "SPY"), quote=True)
    return {
        "enabled": True,
        "kind": kind,
        "html": f'<div class="tradingview-widget" data-kind="{kind}" data-symbol="{safe_symbol}" style="width:{width};height:{height}px"></div>',
        "disclaimer": disclaimer,
        "status": "external_optional",
    }


def build_tradingview_stock_heatmap_embed(*, enabled: bool = False) -> dict[str, Any]:
    return _widget_payload("stock_heatmap", enabled=enabled)


def build_tradingview_market_overview_embed(*, enabled: bool = False) -> dict[str, Any]:
    return _widget_payload("market_overview", enabled=enabled)


def build_tradingview_market_quotes_embed(*, enabled: bool = False, symbol: str = "SPY") -> dict[str, Any]:
    return _widget_payload("market_quotes", enabled=enabled, symbol=symbol, height=320)


def build_tradingview_timeline_embed(*, enabled: bool = False, symbol: str = "SPY") -> dict[str, Any]:
    return _widget_payload("timeline", enabled=enabled, symbol=symbol, height=360)
