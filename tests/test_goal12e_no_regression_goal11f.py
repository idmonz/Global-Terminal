from lib.report_inbox import create_report
from lib.strategy_decision_log import create_strategy_commit
from lib.research_workflow_actions import validate_research_workflow_action


def test_goal12e_goal11f_research_os_apis_still_available(tmp_path):
    db = tmp_path / "workspace.sqlite"
    report = create_report(report_type="manual", title="Goal 12E report", summary="summary", db_path=db)
    assert report["report_id"]
    commit = create_strategy_commit(strategy_id="case_review", message="Case-linked research review", db_path=db)
    assert commit["commit_id"]
    assert validate_research_workflow_action("INSPECT_RELEASE_HYGIENE", {})["ok"] is True
