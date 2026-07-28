from lib.watchlist_store import create_watchlist_item, list_watchlist_items, search_watchlist_items, tag_watchlist_item, delete_watchlist_item


def test_watchlist_crud(tmp_path):
    db=tmp_path/"wl.db"
    item=create_watchlist_item(item_type="chokepoint", display_name="Red Sea", region="Middle East", db_path=db)
    assert list_watchlist_items(db_path=db)[0]["display_name"] == "Red Sea"
    assert search_watchlist_items("red", db)[0]["item_id"] == item["item_id"]
    assert "energy" in tag_watchlist_item(item["item_id"], "energy", db)["tags"]
    delete_watchlist_item(item["item_id"], db)
    assert list_watchlist_items(db_path=db) == []

