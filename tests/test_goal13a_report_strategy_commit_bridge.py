from pathlib import Path

from lib.actionless_simulation_bridge import (
    attach_model_artifact_card_to_report,
    attach_model_artifact_card_to_strategy_commit,
    attach_simulation_case_to_report,
    attach_simulation_case_to_strategy_commit,
)
from lib.actionless_simulation_store import create_actionless_simulation_case, save_model_artifact_card_to_case
from lib.research_artifact_store import list_research_artifacts
from lib.strategy_decision_log import create_strategy_commit


def test_goal13a_report_and_strategy_commit_attachments_are_redacted(tmp_path: Path):
    base = tmp_path / "sims"
    db = tmp_path / "workspace.db"
    create_actionless_simulation_case("Attachment case", objective="Local diagnostic review.", case_id="sim_attach", base_dir=base, source_context={"local_path": str(tmp_path)})
    model = save_model_artifact_card_to_case("sim_attach", {"model_artifact_id": "model_attach", "model_name": "Attachment Card", "category": "regime_model"}, base_dir=base)["model_artifact_card"]

    report_result = attach_simulation_case_to_report("sim_attach", base_dir=base, db_path=db)
    assert report_result["ok"] is True
    assert report_result["attachment"]["attachment_type"] == "actionless_simulation_case"
    assert str(tmp_path) not in str(report_result["attachment"])

    commit = create_strategy_commit(strategy_id="manual_strategy_candidate", message="Manual research snapshot", db_path=db)
    commit_result = attach_simulation_case_to_strategy_commit("sim_attach", commit["commit_id"], base_dir=base, db_path=db)
    assert commit_result["ok"] is True
    artifacts = list_research_artifacts(commit["commit_id"], db)
    assert artifacts[0]["artifact_type"] == "actionless_simulation_case"
    assert str(tmp_path) not in str(artifacts[0])

    model_report = attach_model_artifact_card_to_report(model, db_path=db)
    model_commit = attach_model_artifact_card_to_strategy_commit(commit["commit_id"], model, db_path=db)
    assert model_report["attachment"]["attachment_type"] == "model_artifact_governance_record"
    assert model_commit["artifact"]["artifact_type"] == "model_artifact_governance_record"
