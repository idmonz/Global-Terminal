from pathlib import Path

from lib.actionless_simulation_index import (
    build_simulation_case_index_summary,
    export_simulation_case_index_redacted,
    rebuild_simulation_case_index,
    search_simulation_cases,
)
from lib.actionless_simulation_store import create_actionless_simulation_case, update_actionless_simulation_case


def test_goal13a_simulation_case_index_search_and_summary(tmp_path: Path):
    base = tmp_path / "sims"
    create_actionless_simulation_case("Macro scenario A", objective="Local macro diagnostic review.", case_id="sim_a", base_dir=base, linked_options_case_ids=["opt_a"])
    create_actionless_simulation_case("Commodity scenario B", objective="Local commodity diagnostic review.", case_id="sim_b", base_dir=base)
    update_actionless_simulation_case("sim_b", status="under_review", base_dir=base)

    index = rebuild_simulation_case_index(base_dir=base)
    assert index["case_count"] == 2
    assert search_simulation_cases("commodity", base_dir=base)[0]["case_id"] == "sim_b"
    summary = build_simulation_case_index_summary(base_dir=base)
    assert summary["by_status"]["under_review"] == 1
    redacted = export_simulation_case_index_redacted(base_dir=base)
    assert redacted["case_count"] == 2
    assert "case_dir" not in str(redacted)
