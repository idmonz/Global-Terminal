from lib.command_palette_ui import build_command_palette_state, run_command_palette_action
from lib.watchlist_store import list_watchlist_items


def _run_add(query, db):
    state = build_command_palette_state(query)
    action = next(row for row in state["suggestions"] if row.get("command") == "ADD WATCHLIST")
    return run_command_palette_action(action, query=query, db_path=db)


def test_goal11d_palette_quick_add_e2e_for_object_types(tmp_path):
    db = tmp_path / "workspace.db"
    for query, expected_type in [("AAPL", "equity"), ("BTCUSDT", "crypto"), ("Red Sea", "region"), ("FRED", "provider"), ("Strategy Ensemble #3", "strategy")]:
        result = _run_add(query, db)
        assert result["ok"] is True
        assert result["item"]["item_type"] == expected_type
    items = list_watchlist_items(db_path=db)
    assert len(items) == 5


def test_goal11d_palette_blocked_command_creates_nothing(tmp_path):
    db = tmp_path / "workspace.db"
    state = build_command_palette_state("buy AAPL")
    result = run_command_palette_action(state["suggestions"][0], query="buy AAPL", db_path=db)
    assert result["status"] == "blocked"
    assert list_watchlist_items(db_path=db) == []
