from pathlib import Path

from lib.options_surface_review_store import (
    save_surface_review_item,
    list_surface_review_items,
    load_surface_review_item,
    update_persistent_surface_review_status,
    archive_surface_review_item,
    filter_surface_reviews_by_status,
    build_persistent_surface_review_queue,
    export_surface_review_queue_redacted,
)


def test_goal12e_persistent_surface_review_queue_roundtrip(tmp_path: Path):
    base = tmp_path / "options_cases"
    saved = save_surface_review_item({"anomaly_count": 3, "surface_quality_score": 61}, base_dir=base, case_id="case_a", title="<b>Surface</b>")
    review_id = saved["review_id"]
    assert (base / "surface_review_queue.json").exists()
    assert list_surface_review_items(base_dir=base)[0]["review_id"] == review_id
    assert load_surface_review_item(review_id, base_dir=base)["case_id"] == "case_a"
    updated = update_persistent_surface_review_status(review_id, "reviewed", notes="checked <script>", base_dir=base)
    assert updated["review_item"]["status"] == "reviewed"
    assert "&lt;script&gt;" in updated["review_item"]["review_notes"]
    assert filter_surface_reviews_by_status("reviewed", base_dir=base)[0]["review_id"] == review_id
    archived = archive_surface_review_item(review_id, base_dir=base)
    assert archived["review_item"]["status"] == "archived"
    assert build_persistent_surface_review_queue(base_dir=base)["count"] == 0
    exported = export_surface_review_queue_redacted(base_dir=base)
    assert exported["private_paths_redacted"] is True
    assert "local_path" not in str(exported)
