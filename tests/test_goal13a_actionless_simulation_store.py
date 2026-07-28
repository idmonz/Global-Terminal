from pathlib import Path

import pytest

from lib.actionless_simulation_store import (
    create_actionless_simulation_case,
    export_simulation_case_redacted,
    load_actionless_simulation_case,
    save_data_feed_snapshot_to_case,
    save_model_artifact_card_to_case,
    save_scenario_set_to_case,
    save_simulation_result_to_case,
    save_simulation_review_item,
    update_simulation_review_status,
)


def test_goal13a_private_store_saves_and_exports_redacted_bundle(tmp_path: Path):
    base = tmp_path / "data" / "private" / "actionless_simulations"
    case = create_actionless_simulation_case(
        "Rates shock research case",
        objective="Package scenario diagnostics for local review.",
        case_id="sim_case_a",
        base_dir=base,
        source_context={"private_path": str(tmp_path / "raw.csv")},
        linked_options_case_ids=["opt_case_a"],
    )
    assert case["case_id"] == "sim_case_a"
    assert (base / "sim_case_a" / "case_manifest.json").exists()

    scenario = save_scenario_set_to_case("sim_case_a", {"scenario_id": "scenario_a", "title": "Rates shock", "horizon": "30 days", "asset_universe": ["SPY"]}, base_dir=base)
    feed = save_data_feed_snapshot_to_case("sim_case_a", {"feed_snapshot_id": "feed_a", "data_source_label": "manual snapshot", "coverage": {"local_path": str(tmp_path)}}, base_dir=base)
    model = save_model_artifact_card_to_case("sim_case_a", {"model_artifact_id": "model_a", "model_name": "Scenario Metadata Card", "category": "regime_model"}, base_dir=base)
    result = save_simulation_result_to_case(
        "sim_case_a",
        {"result_id": "result_a", "scenario_id": scenario["scenario_id"], "model_artifact_id": model["model_artifact_id"], "input_snapshot_id": feed["feed_snapshot_id"], "metrics": {"drawdown_proxy": 0.08}},
        base_dir=base,
    )
    review = save_simulation_review_item("sim_case_a", {"review_id": "review_a", "artifact_type": "simulation_result", "artifact_id": result["result_id"], "title": "Result review"}, base_dir=base)
    updated = update_simulation_review_status("sim_case_a", review["review_id"], "reviewed", notes="Reviewed as research-only diagnostics.", base_dir=base)

    loaded = load_actionless_simulation_case("sim_case_a", base_dir=base)
    assert loaded["scenario_ids"] == ["scenario_a"]
    assert updated["review_item"]["status"] == "reviewed"

    exported = export_simulation_case_redacted("sim_case_a", base_dir=base)
    text = str(exported)
    assert "case_dir" not in text
    assert str(tmp_path) not in text
    assert "[local-path-redacted]" in text
    assert exported["export_redacted"] is True


def test_goal13a_private_store_blocks_path_traversal(tmp_path: Path):
    with pytest.raises(ValueError):
        create_actionless_simulation_case("Bad", case_id="../bad", base_dir=tmp_path)
