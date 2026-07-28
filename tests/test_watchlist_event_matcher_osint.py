from lib.watchlist_event_matcher import build_watchlist_osint_context


def test_watchlist_event_matcher_osint():
    ctx=build_watchlist_osint_context([{"title":"BTC derivatives stress", "related_assets":["BTCUSDT"]}], [{"symbol":"BTCUSDT","display_name":"BTCUSDT"}])
    assert ctx["match_count"] == 1

