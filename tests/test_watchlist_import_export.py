from lib.watchlist_import_export import export_watchlist_items, import_watchlist_items
from lib.watchlist_store import create_watchlist_item, list_watchlist_items


def test_watchlist_import_export(tmp_path):
    db1=tmp_path/"w1.db"; db2=tmp_path/"w2.db"
    create_watchlist_item(item_type="provider", display_name="Provider: FRED", db_path=db1)
    payload=export_watchlist_items(db_path=db1)
    import_watchlist_items(payload, db_path=db2)
    assert len(list_watchlist_items(db_path=db2)) == 1

