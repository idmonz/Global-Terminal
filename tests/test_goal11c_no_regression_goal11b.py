from lib.report_inbox_page_layout import build_report_inbox_page_payload
from lib.research_command_palette import route_research_command
from lib.strategy_log_page_layout import build_strategy_log_page_payload
from lib.watchlist_page_layout import build_watchlist_page_payload
from lib.workspace_page_layout import build_workspace_page_payload


def test_goal11c_preserves_goal11b_payload_keys(tmp_path):
    db = tmp_path / "workspace.db"
    workspace = build_workspace_page_payload(db)
    watchlist = build_watchlist_page_payload(db)
    reports = build_report_inbox_page_payload(db)
    strategy = build_strategy_log_page_payload(db)
    assert workspace["cards"] and workspace["nav_cards"] and workspace["quick_actions"]
    assert {"table", "heatmap", "rmi", "volatility", "alert_cards", "alert_timeline"} <= set(watchlist)
    assert {"generators", "reports", "cards", "timeline", "latest"} <= set(reports)
    assert {"commits", "cards", "graph", "review_queue", "latest_guard_cards"} <= set(strategy)
    assert route_research_command("WORKSPACE")["ok"] is True
