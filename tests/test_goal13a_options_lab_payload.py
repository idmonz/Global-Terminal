from pathlib import Path

from lib.actionless_simulation_store import create_actionless_simulation_case, save_model_artifact_card_to_case, save_scenario_set_to_case
from lib.options_lab_page_layout import build_options_lab_page_payload


def test_goal13a_options_lab_payload_exposes_simulation_and_model_governance(tmp_path: Path):
    base = tmp_path / "sims"
    create_actionless_simulation_case("Goal13A Case", objective="Local diagnostic review.", case_id="sim_payload", base_dir=base)
    save_scenario_set_to_case("sim_payload", {"scenario_id": "scenario_payload", "title": "Macro stress", "horizon": "quarter"}, base_dir=base)
    save_model_artifact_card_to_case("sim_payload", {"model_artifact_id": "model_payload", "model_name": "Governance Card", "category": "regime_model"}, base_dir=base)

    payload = build_options_lab_page_payload(
        selected_simulation_case_id="sim_payload",
        simulation_base_dir=str(base),
        simulation_search_query="Goal13A",
    )
    assert "Action-less simulation case index" in payload["sections"]
    assert payload["actionless_simulation_case_index_summary"]["case_count"] == 1
    assert payload["selected_actionless_simulation_case"]["case_manifest"]["case_id"] == "sim_payload"
    assert payload["model_artifact_registry_summary"]["no_runtime"] is True
    assert "SAVE_MODEL_ARTIFACT_CARD" in payload["simulation_case_actions"]
    text = str(payload)
    assert str(tmp_path) not in text
    assert "case_dir" not in text
