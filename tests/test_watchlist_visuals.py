from lib.watchlist_visuals import build_watchlist_row_badges, build_watchlist_summary_cards


def test_watchlist_visual_cards():
    cards=build_watchlist_summary_cards({"count":1,"by_type":{"asset":1}})
    assert cards[0]["value"] == 1
    assert build_watchlist_row_badges({"item_type":"asset","source":"manual"})

