from lib.watchlist_event_matcher import match_events_to_watchlist
from lib.osint_event_deduper import dedupe_events


def test_red_sea_bab_el_mandeb_and_hormuz_aliases_match():
    items = [
        {"item_id": "red", "item_type": "chokepoint", "display_name": "Red Sea", "tags": ["energy"]},
        {"item_id": "oil", "item_type": "commodity", "symbol": "CL1!", "display_name": "WTI Crude", "tags": ["oil"]},
    ]
    events = [
        {"title": "Bab el-Mandeb shipping lane disruption", "summary": "Red Sea cargo stress", "source": "mock"},
        {"title": "Strait of Hormuz tanker risk", "summary": "Oil chokepoint stress", "source": "mock"},
    ]
    matches = match_events_to_watchlist(events, items)
    assert any(m["item_id"] == "red" and "alias" in m["labels"] for m in matches)
    assert any(m["item_id"] == "oil" for m in matches)


def test_btc_crypto_and_fred_provider_aliases_match():
    items = [
        {"item_id": "btc", "item_type": "crypto", "symbol": "BTCUSDT", "display_name": "Bitcoin", "tags": ["crypto"]},
        {"item_id": "fred", "item_type": "provider", "display_name": "Provider: FRED", "tags": ["provider"]},
    ]
    events = [
        {"title": "Bitcoin funding stress rises", "summary": "BTC derivatives update", "source": "mock"},
        {"title": "Federal Reserve Economic Data missing key", "summary": "FRED status caveat", "source": "provider_health"},
    ]
    matches = match_events_to_watchlist(events, items)
    assert any(m["item_id"] == "btc" for m in matches)
    assert any(m["item_id"] == "fred" for m in matches)


def test_duplicate_news_events_are_deduped_and_low_confidence_labeled():
    events = [
        {"title": "Generic regional tension", "source": "mock", "published_at": "2026-06-13T10:01:00Z"},
        {"title": "Generic regional tension", "source": "mock", "published_at": "2026-06-13T10:05:00Z"},
    ]
    assert len(dedupe_events(events)) == 1
    matches = match_events_to_watchlist(events, [{"item_id": "x", "item_type": "event_theme", "display_name": "regional", "tags": ["regional"]}])
    assert matches
    assert matches[0]["labels"]
