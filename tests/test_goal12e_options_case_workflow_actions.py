from pathlib import Path

from lib.options_lab_workflow_actions import run_options_lab_action
from lib.research_workflow_actions import validate_research_workflow_action, run_research_workflow_action


def test_goal12e_options_case_and_review_workflow_actions(tmp_path: Path):
    base = tmp_path / "options_cases"
    created = run_options_lab_action("CREATE_OPTIONS_RESEARCH_CASE", {"case_id": "case1", "title": "Case 1", "base_dir": str(base), "metadata": {"underlying": "BTC"}})
    assert created["case_id"] == "case1"
    indexed = run_options_lab_action("REBUILD_OPTIONS_CASE_INDEX", {"base_dir": str(base)})
    assert indexed["case_count"] == 1
    searched = run_options_lab_action("SEARCH_OPTIONS_CASES", {"base_dir": str(base), "query": "BTC"})
    assert searched["cases"][0]["case_id"] == "case1"
    saved_review = run_options_lab_action("SAVE_SURFACE_REVIEW_ITEM", {"base_dir": str(base), "case_id": "case1", "surface_qa": {"anomaly_count": 2}})
    listed = run_options_lab_action("LIST_SURFACE_REVIEW_QUEUE", {"base_dir": str(base)})
    assert listed["count"] == 1
    updated = run_options_lab_action("UPDATE_PERSISTENT_SURFACE_REVIEW_STATUS", {"base_dir": str(base), "review_id": saved_review["review_id"], "status": "reviewed"})
    assert updated["review_item"]["status"] == "reviewed"
    assert validate_research_workflow_action("SEARCH_OPTIONS_CASES", {"query": "option surface research"})["ok"] is True
    assert validate_research_workflow_action("SEARCH_OPTIONS_CASES", {"query": "execute order"})["ok"] is False
    card = run_research_workflow_action("LIST_SURFACE_REVIEW_QUEUE", {"base_dir": str(base)})
    assert card["ok"] is True
