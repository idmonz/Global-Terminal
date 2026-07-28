from lib.report_inbox import create_report
from lib.strategy_decision_log import create_strategy_commit, get_strategy_commit
from lib.strategy_review_actions import attach_artifact_to_selected_commit, build_selected_strategy_payload, update_selected_strategy_review
from lib.watchlist_store import create_watchlist_item


def test_goal11d_strategy_selection_diff_and_artifact_timeline(tmp_path):
    db = tmp_path / "workspace.db"
    parent = create_strategy_commit(strategy_id="candidate", message="parent", strategy_config_snapshot={"window": 10}, db_path=db)
    child = create_strategy_commit(strategy_id="candidate", message="child", parent_commit_id=parent["commit_id"], strategy_config_snapshot={"window": 20}, db_path=db)
    payload = build_selected_strategy_payload(child["commit_id"], db_path=db)
    assert payload["selected_commit_id"] == child["commit_id"]
    assert payload["diff_panel"]["compare_to"] == parent["commit_id"]
    assert payload["guard_dashboard"]["title"] == "Guard dashboard"

    status = update_selected_strategy_review(child["commit_id"], "requires_review", note="guard follow-up", db_path=db)
    assert status["ok"] is True
    assert get_strategy_commit(child["commit_id"], db)["review_status"] == "requires_review"

    report = create_report(report_type="strategy", title="Strategy report", db_path=db)
    item = create_watchlist_item(item_type="strategy", display_name="Strategy Ensemble #3", db_path=db)
    assert attach_artifact_to_selected_commit(child["commit_id"], report_id=report["report_id"], db_path=db)["ok"] is True
    attach = attach_artifact_to_selected_commit(child["commit_id"], watchlist_item_id=item["item_id"], db_path=db)
    assert attach["ok"] is True
    assert len(attach["timeline"]) >= 2
    text = str(build_selected_strategy_payload(child["commit_id"], db_path=db)).lower()
    assert "approval" not in text
