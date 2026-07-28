from pathlib import Path

from lib.options_research_case_store import create_options_research_case, save_surface_qa_to_case, update_options_research_case_status
from lib.options_research_case_index import (
    rebuild_options_case_index,
    search_options_research_cases,
    filter_options_cases_by_status,
    filter_options_cases_by_underlying,
    filter_options_cases_by_tag,
    build_options_case_index_summary,
    export_options_case_index_redacted,
)


def test_goal12e_options_case_index_search_filter_and_redaction(tmp_path: Path):
    base = tmp_path / "options_cases"
    create_options_research_case("BTC Surface Case", case_id="btc_case", base_dir=base, metadata={"underlying": "BTC", "tags": ["surface", "qa"], "source": "/mnt/private/source.csv"})
    save_surface_qa_to_case("btc_case", {"anomaly_count": 2, "absolute_path": "/mnt/data/private/leak.json"}, base_dir=base)
    update_options_research_case_status("btc_case", "requires_review", base_dir=base, metadata={"review_status": "requires_review", "surface_quality_score": 78})
    index = rebuild_options_case_index(base_dir=base)
    assert index["case_count"] == 1
    assert search_options_research_cases("btc", base_dir=base)[0]["case_id"] == "btc_case"
    assert filter_options_cases_by_status("requires_review", base_dir=base)[0]["case_id"] == "btc_case"
    assert filter_options_cases_by_underlying("BTC", base_dir=base)[0]["case_id"] == "btc_case"
    assert filter_options_cases_by_tag("qa", base_dir=base)[0]["case_id"] == "btc_case"
    summary = build_options_case_index_summary(base_dir=base)
    assert summary["case_count"] == 1
    exported = export_options_case_index_redacted(base_dir=base)
    text = str(exported)
    assert "case_dir" not in text
    assert "/mnt/data" not in text
    assert exported["private_paths_redacted"] is True
    assert (base / "case_index.json").exists()
