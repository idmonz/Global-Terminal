from lib.research_command_safety import detect_forbidden_command_intent
from lib.report_inbox import create_report
from lib.strategy_decision_log import create_strategy_commit


def test_goal11f_safety_report_and_commit_paths_still_work(tmp_path):
    assert detect_forbidden_command_intent("execute order BTC")["blocked"] is True
    db=tmp_path/"workspace.sqlite"
    report=create_report(report_type="Watchlist Brief", title="Goal12B regression report", db_path=db)
    commit=create_strategy_commit(strategy_id="goal12b", message="research record", linked_reports=[report["report_id"]], db_path=db)
    assert report["report_id"] in commit["linked_reports"]
