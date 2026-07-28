from pathlib import Path

from lib.actionless_simulation_workflow import run_actionless_simulation_workflow
from lib.options_lab_workflow_actions import run_options_lab_action
from lib.research_workflow_actions import validate_research_workflow_action


def test_goal13a_workflow_actions_create_save_search_export(tmp_path: Path):
    base = tmp_path / "sims"
    created = run_options_lab_action("CREATE_SIMULATION_CASE", {"case_id": "sim_case", "title": "Scenario case", "objective": "Local diagnostic review.", "base_dir": str(base)})
    assert created["case_id"] == "sim_case"
    assert run_options_lab_action("SAVE_SCENARIO_SET", {"case_id": "sim_case", "base_dir": str(base), "scenario_set": {"scenario_id": "scenario_1", "title": "Volatility stress", "horizon": "30 days"}})["ok"]
    assert run_options_lab_action("SAVE_DATA_FEED_SNAPSHOT", {"case_id": "sim_case", "base_dir": str(base), "feed_snapshot": {"feed_snapshot_id": "feed_1", "data_source_label": "manual"}})["ok"]
    assert run_options_lab_action("SAVE_MODEL_ARTIFACT_CARD", {"case_id": "sim_case", "base_dir": str(base), "model_artifact_card": {"model_artifact_id": "model_1", "model_name": "Metadata card", "category": "regime_model"}})["ok"]
    assert run_options_lab_action("SAVE_SIMULATION_RESULT", {"case_id": "sim_case", "base_dir": str(base), "simulation_result": {"result_id": "result_1", "scenario_id": "scenario_1", "model_artifact_id": "model_1", "input_snapshot_id": "feed_1"}})["ok"]
    indexed = run_options_lab_action("BUILD_SIMULATION_CASE_INDEX", {"base_dir": str(base)})
    assert indexed["case_count"] == 1
    searched = run_options_lab_action("SEARCH_SIMULATION_CASES", {"base_dir": str(base), "query": "Scenario"})
    assert searched["cases"][0]["case_id"] == "sim_case"
    exported = run_options_lab_action("EXPORT_SIMULATION_CASE_REDACTED", {"base_dir": str(base), "case_id": "sim_case"})
    assert exported["export_redacted"] is True


def test_goal13a_workflow_rejects_action_language_and_research_validator_blocks_query(tmp_path: Path):
    base = tmp_path / "sims"
    run_actionless_simulation_workflow("CREATE_SIMULATION_CASE", {"case_id": "safe_case", "title": "Safe case", "objective": "Local diagnostic review.", "base_dir": str(base)})
    rejected = run_actionless_simulation_workflow("UPDATE_SIMULATION_CASE", {"case_id": "safe_case", "base_dir": str(base), "objective": "Execute order now"})
    assert rejected["ok"] is False
    assert "action_language_blocked" in rejected["message"]
    assert validate_research_workflow_action("SEARCH_SIMULATION_CASES", {"query": "scenario research"})["ok"] is True
    assert validate_research_workflow_action("SEARCH_SIMULATION_CASES", {"query": "execute order"})["ok"] is False
