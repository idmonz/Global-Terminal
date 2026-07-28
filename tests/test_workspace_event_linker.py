from lib.workspace_event_linker import match_events_to_watchlist, match_regions_to_watchlist, match_chokepoints_to_watchlist, match_providers_to_watchlist


def test_workspace_event_linker():
    items=[{"display_name":"Hormuz", "item_type":"chokepoint"},{"display_name":"Provider: FRED", "item_type":"provider"}]
    events=[{"title":"Hormuz risk elevated", "region":"Hormuz"}]
    assert match_events_to_watchlist(events, items)
    assert match_regions_to_watchlist(events, items)
    assert match_chokepoints_to_watchlist(events, items)
    assert match_providers_to_watchlist([{"provider_name":"Provider: FRED", "status":"missing-key"}], items)

