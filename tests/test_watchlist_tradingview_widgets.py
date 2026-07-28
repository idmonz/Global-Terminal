from lib.watchlist_tradingview_widgets import build_watchlist_market_quotes_widget, build_watchlist_tradingview_disclaimer


def test_tradingview_optional_only():
    payload=build_watchlist_market_quotes_widget(["SPY"], enabled=False)
    assert payload["enabled"] is False
    assert "not used for calculations" in build_watchlist_tradingview_disclaimer()["text"]

