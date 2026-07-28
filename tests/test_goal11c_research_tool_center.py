from lib.research_tool_center import build_research_tool_center_payload
from lib.terminal_function_registry import get_function_definition


def test_goal11c_research_tool_center_catalog_and_route():
    payload = build_research_tool_center_payload()
    assert payload["tool_count"] >= 10
    for section in payload["sections"]:
        for tool in section["tools"]:
            assert tool["research_only"] is True
            assert tool["caveat"]
            text = " ".join(str(v).lower() for v in tool.values())
            assert "place_order" not in text
    assert get_function_definition("TOOL CENTER")["page"] == "pages/23_Research_Tool_Center.py"
