from lib.report_inbox import create_report
from lib.report_reader_workflow import build_report_reader_workflow_state, update_selected_report_review
from lib.strategy_decision_log import create_strategy_commit
from lib.strategy_review_actions import build_selected_strategy_payload, update_selected_strategy_review


def test_goal11e_selected_report_persists_after_review_update(tmp_path):
    db = tmp_path / "workspace.db"
    r1 = create_report(report_type="watchlist", title="First", summary="one", db_path=db)
    r2 = create_report(report_type="provider_health", title="Second", summary="two", db_path=db)
    state = {"selected_report_id": r2["report_id"], "report_filters": {"report_type": "all", "review_status": "all", "query": ""}}
    before = build_report_reader_workflow_state(selected_report_id=r2["report_id"], db_path=db, session_state=state)
    assert before["selected_report"]["title"] == "Second"
    update = update_selected_report_review(r2["report_id"], "reviewed", notes="done", db_path=db, session_state=state)
    assert update["workflow_state"]["selected_report_id"] == r2["report_id"]
    assert state["selected_report_id"] == r2["report_id"]
    assert state["last_action_result"]["action"] == "UPDATE_REPORT_REVIEW_STATUS"


def test_goal11e_filter_state_keeps_selected_row_unless_filtered_out(tmp_path):
    db = tmp_path / "workspace.db"
    r1 = create_report(report_type="watchlist", title="Alpha", summary="one", db_path=db)
    r2 = create_report(report_type="provider_health", title="Beta", summary="two", db_path=db)
    state = {"selected_report_id": r2["report_id"], "report_filters": {"report_type": "all", "review_status": "all", "query": ""}}
    same = build_report_reader_workflow_state(report_type="all", review_status="all", db_path=db, session_state=state)
    assert same["selected_report_id"] == r2["report_id"]
    filtered = build_report_reader_workflow_state(report_type="watchlist", review_status="all", db_path=db, session_state=state)
    assert filtered["selected_report_id"] == r1["report_id"]


def test_goal11e_selected_strategy_commit_persists_after_review_update(tmp_path):
    db = tmp_path / "workspace.db"
    c1 = create_strategy_commit(strategy_id="alpha", message="parent", db_path=db)
    c2 = create_strategy_commit(strategy_id="beta", message="child", parent_commit_id=c1["commit_id"], db_path=db)
    state = {"selected_strategy_commit_id": c2["commit_id"]}
    before = build_selected_strategy_payload(db_path=db, session_state=state)
    assert before["selected_commit_id"] == c2["commit_id"]
    update = update_selected_strategy_review(c2["commit_id"], "reviewed", note="checked", db_path=db, session_state=state)
    assert update["workflow_state"]["selected_commit_id"] == c2["commit_id"]
    assert state["selected_strategy_commit_id"] == c2["commit_id"]
    assert state["last_action_result"]["action"] == "UPDATE_STRATEGY_REVIEW_STATUS"
