from lib.research_workflow_actions import run_research_workflow_action
from lib.report_inbox import get_report, list_reports
from lib.strategy_decision_log import create_strategy_commit, get_strategy_commit
from lib.watchlist_store import list_watchlist_items
from lib.workspace_activity_log import list_workspace_activity


def test_goal11d_quick_add_report_and_review_actions_mutate_db(tmp_path):
    db = tmp_path / "workspace.db"
    added = run_research_workflow_action("ADD_WATCHLIST_ITEM", {"query": "AAPL"}, db_path=db)
    assert added["ok"] is True
    assert list_watchlist_items(db_path=db)[0]["display_name"] == "AAPL"

    report_result = run_research_workflow_action("GENERATE_WATCHLIST_BRIEF", {"title": "Watchlist workflow brief"}, db_path=db)
    assert report_result["ok"] is True
    report_id = report_result["report"]["report_id"]
    review = run_research_workflow_action("UPDATE_REPORT_REVIEW_STATUS", {"report_id": report_id, "status": "reviewed", "notes": "checked"}, db_path=db)
    assert review["ok"] is True
    assert get_report(report_id, db)["report_review_status"] == "reviewed"
    assert list_workspace_activity(db_path=db)


def test_goal11d_strategy_actions_and_blocked_action_do_not_mutate(tmp_path):
    db = tmp_path / "workspace.db"
    before = len(list_watchlist_items(db_path=db))
    blocked = run_research_workflow_action("MARKET_ORDER", {"symbol": "AAPL"}, db_path=db)
    assert blocked["status"] == "error"
    assert len(list_watchlist_items(db_path=db)) == before

    commit_result = run_research_workflow_action("CREATE_STRATEGY_COMMIT", {"strategy_id": "candidate_alpha", "message": "manual review note"}, db_path=db)
    assert commit_result["ok"] is True
    commit_id = commit_result["commit"]["commit_id"]
    status = run_research_workflow_action("UPDATE_STRATEGY_REVIEW_STATUS", {"commit_id": commit_id, "status": "reviewed", "note": "ok"}, db_path=db)
    assert status["ok"] is True
    assert get_strategy_commit(commit_id, db)["review_status"] == "reviewed"
