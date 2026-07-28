from lib.options_attachment_bridge import attach_options_result_to_report, build_options_attachment
from lib.options_report_generator import generate_options_pricing_report
from lib.options_strategy_commit_bridge import attach_options_result_to_strategy_commit
from lib.research_artifact_store import list_research_artifacts
from lib.strategy_decision_log import create_strategy_commit

INPUT = {"option_type": "call", "underlying_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2}


def test_options_attachment_builds_supported_type():
    result = generate_options_pricing_report(INPUT, persist=False)
    attachment = build_options_attachment(result)
    assert attachment["attachment_type"] == "option_analysis_snapshot"


def test_options_result_attaches_to_report_and_commit(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    result = generate_options_pricing_report(INPUT, persist=False)
    report_result = attach_options_result_to_report(result, db_path=db)
    assert report_result["ok"] is True
    commit = create_strategy_commit(strategy_id="goal12a_test", message="Attach research-only options result", db_path=db)
    attach = attach_options_result_to_strategy_commit(commit["commit_id"], result, db_path=db)
    assert attach["ok"] is True
    artifacts = list_research_artifacts(commit["commit_id"], db_path=db)
    assert artifacts and artifacts[0]["artifact_type"] == "option_analysis_snapshot"
