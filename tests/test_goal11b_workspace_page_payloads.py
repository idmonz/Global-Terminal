from lib.workspace_page_layout import build_workspace_page_payload
from lib.watchlist_page_layout import build_watchlist_page_payload
from lib.report_inbox_page_layout import build_report_inbox_page_payload
from lib.strategy_log_page_layout import build_strategy_log_page_payload
from lib.watchlist_store import create_watchlist_item
from lib.report_generators import generate_watchlist_brief
from lib.strategy_decision_log import create_strategy_commit


def test_workspace_page_payload_has_cards_empty_states_and_nav(tmp_path):
    db = tmp_path / "research.db"
    payload = build_workspace_page_payload(db)
    assert payload["cards"]
    assert payload["empty_states"]["no_watchlist_items"] is True
    assert any(card["command"] == "WATCHLIST" for card in payload["nav_cards"])


def test_watchlist_report_and_strategy_page_payloads(tmp_path):
    db = tmp_path / "research.db"
    create_watchlist_item(item_type="asset", symbol="AAPL", display_name="Apple", db_path=db)
    watch_payload = build_watchlist_page_payload(db, supplied_context={"market": {"AAPL": {"latest_value": 1, "change_pct": 0.1}}})
    assert watch_payload["table"][0]["latest_value"] == 1
    generate_watchlist_brief(db_path=db)
    report_payload = build_report_inbox_page_payload(db)
    assert report_payload["cards"]
    create_strategy_commit(strategy_id="s", message="Research record", db_path=db)
    strategy_payload = build_strategy_log_page_payload(db)
    assert strategy_payload["graph"]["commit_count"] == 1
    assert strategy_payload["latest_guard_cards"]
