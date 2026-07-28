from lib.workspace_store import get_workspace_counts
from lib.watchlist_store import create_watchlist_item


def test_workspace_counts(tmp_path):
    db=tmp_path/"s.db"
    create_watchlist_item(item_type="asset", symbol="AAPL", display_name="Apple", db_path=db)
    assert get_workspace_counts(db)["watchlist_items"] == 1

