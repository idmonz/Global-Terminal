from lib.research_workspace_db import export_workspace_json, import_workspace_json
from lib.watchlist_store import create_watchlist_item, list_watchlist_items


def test_workspace_export_import_roundtrip(tmp_path):
    db1 = tmp_path / "a.db"; db2 = tmp_path / "b.db"
    create_watchlist_item(item_type="crypto", symbol="BTCUSDT", display_name="BTC", db_path=db1)
    payload = export_workspace_json(db1)
    result = import_workspace_json(payload, db2)
    assert result["imported"]["watchlist_items"] == 1
    assert list_watchlist_items(db_path=db2)[0]["symbol"] == "BTCUSDT"

