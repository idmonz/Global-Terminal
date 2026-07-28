from __future__ import annotations

from lib.tradingview_widget_embed import build_tradingview_market_overview_embed, build_tradingview_widget_disclaimer


def test_tradingview_widgets_are_optional_supplements():
    disabled = build_tradingview_market_overview_embed()
    assert disabled["enabled"] is False
    assert "not used for calculations" in build_tradingview_widget_disclaimer()["text"]
