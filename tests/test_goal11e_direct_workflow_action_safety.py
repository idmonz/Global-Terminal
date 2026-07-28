from lib.research_workflow_actions import run_research_workflow_action
from lib.watchlist_store import list_watchlist_items


def test_goal11e_direct_forbidden_watchlist_add_returns_boundary_card_without_mutation(tmp_path):
    db = tmp_path / "workspace.db"
    before = len(list_watchlist_items(db_path=db))
    result = run_research_workflow_action("ADD_WATCHLIST_ITEM", {"query": "buy AAPL"}, db_path=db)
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["blocked_card"]["status"] == "blocked"
    assert result["safe_alternatives"]
    assert len(list_watchlist_items(db_path=db)) == before


def test_goal11e_supported_direct_watchlist_add_still_mutates_once(tmp_path):
    db = tmp_path / "workspace.db"
    result = run_research_workflow_action("ADD_WATCHLIST_ITEM", {"query": "AAPL"}, db_path=db)
    assert result["ok"] is True
    items = list_watchlist_items(db_path=db)
    assert len(items) == 1
    assert items[0]["display_name"] == "AAPL"


def test_goal11e_export_workspace_action_returns_single_export_payload(tmp_path):
    db = tmp_path / "workspace.db"
    run_research_workflow_action("ADD_WATCHLIST_ITEM", {"query": "AAPL"}, db_path=db)
    result = run_research_workflow_action("EXPORT_WORKSPACE_JSON", {}, db_path=db)
    assert result["ok"] is True
    assert "export" in result
    assert isinstance(result["export"].get("tables"), dict)
