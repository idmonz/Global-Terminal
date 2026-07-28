from lib.watchlist_event_matcher import match_events_to_watchlist, build_watchlist_event_summary


def test_watchlist_event_matcher():
    events=[{"title":"Red Sea shipping disruption", "region":"Red Sea", "confidence":0.7}]
    items=[{"display_name":"Red Sea", "item_type":"chokepoint", "tags":["shipping"]}]
    assert match_events_to_watchlist(events, items)
    assert build_watchlist_event_summary(events, items)["matched_events"] == 1

