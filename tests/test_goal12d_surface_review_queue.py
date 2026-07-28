from lib.options_surface_review_queue import (
    build_surface_review_cards,
    build_surface_review_queue,
    create_surface_review_item,
    update_surface_review_status,
)


def test_goal12d_surface_review_queue_lifecycle():
    item = create_surface_review_item({"anomaly_count": 2}, case_id="case_a")
    assert item["status"] == "requires_review"
    reviewed = update_surface_review_status(item, "reviewed", notes="checked")
    assert reviewed["status"] == "reviewed"
    queue = build_surface_review_queue([item, reviewed, {**reviewed, "status":"archived"}])
    assert queue["count"] == 2
    assert build_surface_review_cards(queue["items"])[0]["review_id"] == item["review_id"]
