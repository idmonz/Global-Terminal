from lib.watchlist_market_context import build_watchlist_market_context


def test_watchlist_market_context_missing_is_labeled():
    ctx = build_watchlist_market_context([{"symbol":"AAPL", "display_name":"Apple"}])
    assert ctx["rows"][0]["freshness"] == "missing"

