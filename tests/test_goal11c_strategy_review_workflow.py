from lib.research_artifact_store import store_research_artifact
from lib.strategy_artifact_timeline import build_strategy_artifact_timeline
from lib.strategy_decision_log import create_strategy_commit, get_strategy_commit
from lib.strategy_log_page_layout import build_strategy_log_page_payload
from lib.strategy_review_workflow import update_strategy_review_status


def test_goal11c_strategy_review_status_and_artifact_timeline(tmp_path):
    db = tmp_path / "workspace.db"
    commit = create_strategy_commit(strategy_id="candidate_alpha", message="Research note", db_path=db)
    store_research_artifact(commit["commit_id"], "report", "Initial report", db_path=db)
    payload = build_strategy_log_page_payload(db)
    assert payload["review_queue"]
    assert payload["commit_reader"]["guard_summary"]
    assert payload["guard_dashboard"]["title"] == "Guard dashboard"
    timeline = build_strategy_artifact_timeline(commit["commit_id"], db_path=db)
    assert timeline["events"][0]["title"] == "Initial report"
    result = update_strategy_review_status(commit["commit_id"], "reviewed", note="checked", db_path=db)
    assert result["ok"] is True
    assert get_strategy_commit(commit["commit_id"], db)["review_status"] == "reviewed"
