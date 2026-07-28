from lib.research_command_safety import detect_forbidden_command_intent
from lib.research_tool_center import build_research_tool_center_payload
from lib.terminal_command_router import route_terminal_command


def test_goal11f_command_safety_still_blocks_actionable_boundary():
    for text in ["recommend NVDA", "recommended portfolio", "recommendation TSLA", "best portfolio", "guaranteed return strategy"]:
        assert detect_forbidden_command_intent(text)["blocked"] is True
        assert route_terminal_command(text)["ok"] is False


def test_existing_tool_center_sections_still_present():
    sections = {section["section"] for section in build_research_tool_center_payload()["sections"]}
    assert "Data Provider Tools" in sections
    assert "Strategy Review Tools" in sections
