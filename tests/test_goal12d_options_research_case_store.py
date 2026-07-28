from lib.options_research_case_store import (
    build_case_timeline,
    create_options_research_case,
    export_case_manifest_redacted,
    list_options_research_cases,
    load_options_research_case,
    save_chain_snapshot_to_case,
    save_option_book_stress_to_case,
    save_quant_diagnostics_to_case,
    save_surface_qa_to_case,
    save_surface_snapshot_to_case,
)


def test_goal12d_options_case_store_persists_private_artifacts(tmp_path):
    root = tmp_path / "data" / "private" / "options_cases"
    case = create_options_research_case("<Case>", case_id="case_a", base_dir=root, metadata={"local_path":"/mnt/data/private.csv"})
    assert case["case_id"] == "case_a"
    assert case["private_storage"] is True
    assert (root / "case_a" / "case_manifest.json").exists()
    assert save_chain_snapshot_to_case("case_a", {"underlying":"SPY"}, base_dir=root)["ok"]
    assert save_surface_snapshot_to_case("case_a", {"points":[]}, base_dir=root)["ok"]
    assert save_surface_qa_to_case("case_a", {"anomaly_count":1}, base_dir=root)["ok"]
    assert save_option_book_stress_to_case("case_a", {"rows":[]}, base_dir=root)["ok"]
    assert save_quant_diagnostics_to_case("case_a", {"assets":["SPY"]}, base_dir=root)["ok"]
    loaded = load_options_research_case("case_a", base_dir=root)
    assert "surface_qa" in loaded["artifacts"]
    assert len(build_case_timeline("case_a", base_dir=root)) >= 6
    exported = export_case_manifest_redacted("case_a", base_dir=root)
    assert "case_dir" not in exported
    assert "[local-path-redacted]" in str(exported)
    assert list_options_research_cases(base_dir=root)[0]["case_id"] == "case_a"


def test_goal12d_options_case_store_blocks_path_traversal(tmp_path):
    root = tmp_path / "cases"
    try:
        create_options_research_case("bad", case_id="../bad", base_dir=root)
    except ValueError as exc:
        assert "invalid_case_id" in str(exc) or "traversal" in str(exc)
    else:
        raise AssertionError("path traversal case id accepted")
