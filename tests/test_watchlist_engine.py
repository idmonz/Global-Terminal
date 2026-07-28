from lib.watchlist_store import create_watchlist_item
from lib.watchlist_engine import build_watchlist_context, build_watchlist_heatmap_payload, build_watchlist_rmi_payload, build_watchlist_volatility_payload


def test_watchlist_payloads(tmp_path):
    db=tmp_path/"we.db"; create_watchlist_item(item_type="asset", symbol="SPY", display_name="SPY", db_path=db)
    assert build_watchlist_context(db)["summary"]["count"] == 1
    assert build_watchlist_heatmap_payload(db)["tiles"]
    assert build_watchlist_rmi_payload(db)["rows"]
    assert build_watchlist_volatility_payload(db)["rows"]

