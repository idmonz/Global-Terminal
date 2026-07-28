from pathlib import Path

from lib.options_research_case_store import create_options_research_case, save_chain_snapshot_to_case
from lib.options_research_case_index import rebuild_options_case_index, export_options_case_index_redacted
from lib.options_surface_review_store import save_surface_review_item, update_persistent_surface_review_status, export_surface_review_queue_redacted


def test_goal12e_case_index_uses_metadata_source_and_redacts_absolute_paths(tmp_path: Path):
    base = tmp_path / "options_cases"
    case = create_options_research_case(
        title="AAPL case",
        metadata={"underlying": "AAPL", "source": "csv_upload", "tags": ["vol"], "local_path": "/secret/path"},
        base_dir=base,
    )
    save_chain_snapshot_to_case(case["case_id"], {"rows": [{"symbol": "AAPL", "local_path": "/secret/path"}]}, base_dir=base)
    rebuild_options_case_index(base_dir=base)
    exported = export_options_case_index_redacted(base_dir=base)
    text = str(exported)
    assert exported["entries"][0]["source"] == "csv_upload"
    assert "/secret/path" not in text
    assert "local-path-redacted" in str(case) or exported["private_paths_redacted"] is True


def test_goal12e_surface_review_export_redacts_generic_absolute_paths(tmp_path: Path):
    result = save_surface_review_item({"status": "new", "title": "Review"}, base_dir=tmp_path)
    review_id = result["review_id"]
    update_persistent_surface_review_status(review_id, "requires_review", notes="check /secret/path and C:\\private\\file", base_dir=tmp_path)
    exported = export_surface_review_queue_redacted(base_dir=tmp_path)
    text = str(exported)
    assert "/secret/path" not in text
    assert "C:\\private" not in text
    assert "[local-path-redacted]" in text
