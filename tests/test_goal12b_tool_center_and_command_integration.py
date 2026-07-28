from lib.research_tool_actions import get_research_tool_definition, run_research_tool_action
from lib.research_workflow_actions import SAFE_RESEARCH_ACTIONS
from lib.terminal_command_router import route_terminal_command
from lib.terminal_function_registry import get_function_definition


def test_goal12b_tool_center_and_commands_are_safe_routes():
    assert get_research_tool_definition("Import Option Chain CSV")["workflow_action"] == "IMPORT_OPTION_CHAIN_CSV"
    assert "RUN_LOCAL_QUANT_DIAGNOSTICS" in SAFE_RESEARCH_ACTIONS
    assert get_function_definition("VOL SURFACE")["page"].endswith("24_Options_Quant_Model_Lab.py")
    assert route_terminal_command("OPTION BOOK")["ok"] is True
    result = run_research_tool_action("Run Local Quant Diagnostics", {"prices_by_asset":{"A":[1,2,3],"B":[1,2.1,2.9]}})
    assert result["status"] == "ok"
