from lib.options_lab_page_layout import build_options_lab_page_payload
from lib.options_lab_workflow_actions import run_options_lab_action
from lib.research_tool_actions import get_research_tool_definition
from lib.terminal_command_router import route_terminal_command


def test_goal12d_options_lab_case_workflow_payload_and_actions(tmp_path):
    root = tmp_path / "cases"
    created = run_options_lab_action("CREATE_OPTIONS_RESEARCH_CASE", {"case_id":"case_a", "title":"Case A", "base_dir":str(root)})
    assert created["case_id"] == "case_a"
    saved = run_options_lab_action("SAVE_CHAIN_TO_CASE", {"case_id":"case_a", "base_dir":str(root), "chain_snapshot":{"rows":[]}})
    assert saved["ok"] is True
    payload = build_options_lab_page_payload(selected_case_id="case_a", case_base_dir=str(root))
    assert "Research Case selector" in payload["sections"]
    assert payload["selected_case"]["case_id"] == "case_a"
    assert payload["case_timeline_panel"] is not None
    assert get_research_tool_definition("Create Options Research Case")["workflow_action"] == "CREATE_OPTIONS_RESEARCH_CASE"
    assert route_terminal_command("OPTIONS CASE")["ok"] is True
    assert route_terminal_command("SURFACE REVIEW")["ok"] is True
