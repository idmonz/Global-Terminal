from lib.command_palette_ui import build_command_palette_state
from lib.intel_feed_engine import build_intel_feed
from lib.report_inbox_page_layout import build_report_inbox_page_payload
from lib.strategy_log_page_layout import build_strategy_log_page_payload
from lib.watchlist_page_layout import build_watchlist_page_payload
from lib.workspace_page_layout import build_workspace_page_payload


def test_goal11d_preserves_goal11c_payloads(tmp_path):
    db = tmp_path / "workspace.db"
    assert build_workspace_page_payload(db)["command_palette"]
    assert "source_freshness" in build_watchlist_page_payload(db)
    assert "reader_panel" in build_report_inbox_page_payload(db)
    assert "review_queue" in build_strategy_log_page_payload(db)
    assert build_intel_feed([])["no_fake_live_data"] is True
    assert build_command_palette_state("AAPL")["result_cards"]
