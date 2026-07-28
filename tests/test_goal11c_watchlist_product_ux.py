from lib.watchlist_alert_builder_ui import build_watchlist_alert_builder_payload
from lib.watchlist_detail_panel import build_watchlist_detail_panel
from lib.watchlist_news_event_grid import build_watchlist_news_event_grid
from lib.watchlist_page_layout import build_watchlist_page_payload
from lib.watchlist_store import create_watchlist_item
from lib.watchlist_table_columns import WATCHLIST_PRODUCT_COLUMNS, build_watchlist_table_columns


def test_goal11c_watchlist_product_payload_has_required_columns(tmp_path):
    db = tmp_path / "workspace.db"
    create_watchlist_item(item_type="crypto", symbol="BTCUSDT", display_name="BTCUSDT", region="Global", db_path=db)
    payload = build_watchlist_page_payload(db)
    assert payload["action_cards"]
    assert payload["detail_panel"]["provider_caveats"]
    assert payload["alert_builder"]["dedupe_supported"] is True
    first = payload["product_table"][0]
    for column in WATCHLIST_PRODUCT_COLUMNS:
        assert column in first


def test_goal11c_watchlist_event_grid_dedupes_and_no_fake_context():
    events = [
        {"title": "Red Sea disruption", "source": "feed", "created_at": "2026-06-14T00:00:00+00:00", "severity": "high"},
        {"title": "Red Sea disruption", "source": "feed", "created_at": "2026-06-14T01:00:00+00:00", "severity": "high"},
    ]
    grid = build_watchlist_news_event_grid(events)
    assert len(grid["rows"]) == 1
    assert grid["no_fake_live_data"] is True
    assert build_watchlist_table_columns([]) == []
    assert build_watchlist_detail_panel(None)["empty"] is True
    assert build_watchlist_alert_builder_payload({"item_id": "x"})["watch_item_id"] == "x"
