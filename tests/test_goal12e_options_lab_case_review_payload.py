from pathlib import Path

from lib.options_lab_page_layout import build_options_lab_page_payload
from lib.options_research_case_store import create_options_research_case
from lib.options_surface_review_store import save_surface_review_item


def test_goal12e_options_lab_payload_exposes_case_index_and_review_queue_without_private_paths(tmp_path: Path):
    base = tmp_path / "options_cases"
    create_options_research_case("ETH Case", case_id="eth_case", base_dir=base, metadata={"underlying": "ETH", "tags": ["surface"]})
    review = save_surface_review_item({"anomaly_count": 1}, base_dir=base, case_id="eth_case", title="ETH Review")
    payload = build_options_lab_page_payload(
        input_data={"underlying_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.01, "volatility": 0.2, "option_type": "call", "model": "black_scholes"},
        selected_case_id="eth_case",
        selected_review_id=review["review_id"],
        case_base_dir=str(base),
        case_search_query="ETH",
    )
    assert payload["demo_mode"] is False
    assert payload["case_index_summary"]["case_count"] == 1
    assert payload["case_search_filter_payload"]["results"][0]["case_id"] == "eth_case"
    assert payload["persistent_surface_review_queue_summary"]["count"] == 1
    assert payload["selected_review_item_panel"]["review_id"] == review["review_id"]
    assert "REBUILD_OPTIONS_CASE_INDEX" in payload["persistent_review_actions"] or "LIST_SURFACE_REVIEW_QUEUE" in payload["persistent_review_actions"]
    text = str(payload)
    assert str(tmp_path) not in text
    assert "case_dir" not in text
    assert payload["raw_payload_expanders_only"] is True
