from lib.quant_model_attachment_bridge import attach_model_snapshot_to_strategy_commit
from lib.quant_model_lab import build_quant_model_lab_payload, create_quant_model_snapshot, simple_deterministic_diagnostics
from lib.quant_model_report_generator import attach_model_snapshot_to_report
from lib.quant_model_registry import build_model_registry_payload
from lib.research_artifact_store import list_research_artifacts
from lib.strategy_decision_log import create_strategy_commit


def test_deterministic_diagnostics_and_registry():
    diagnostics = simple_deterministic_diagnostics([1, 2, 3])
    assert diagnostics["count"] == 3
    assert diagnostics["mean"] == 2
    assert build_model_registry_payload()["models"]


def test_quant_model_snapshot_report_and_commit_attachment(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    snapshot = create_quant_model_snapshot(values=[1, 2, 3])
    report = attach_model_snapshot_to_report(snapshot, db_path=db)
    assert report["ok"] is True
    commit = create_strategy_commit(strategy_id="model_snapshot_test", message="Attach quant model snapshot", db_path=db)
    attach = attach_model_snapshot_to_strategy_commit(commit["commit_id"], snapshot, db_path=db)
    assert attach["ok"] is True
    assert list_research_artifacts(commit["commit_id"], db_path=db)
    assert build_quant_model_lab_payload()["ok"] is True
