from lib.research_tool_actions import get_research_tool_definition, run_research_tool_action, search_research_tools
from lib.research_tool_center import build_research_tool_center_payload

INPUT = {"option_type": "call", "underlying_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2}


def test_tool_center_exposes_goal12a_tools():
    payload = build_research_tool_center_payload()
    names = {tool["tool_name"] for section in payload["sections"] for tool in section["tools"]}
    assert "Price Option" in names
    assert "Create Quant Model Snapshot" in names
    assert search_research_tools("implied volatility")


def test_tool_action_routes_price_option():
    definition = get_research_tool_definition("Price Option")
    assert definition and definition["workflow_action"] == "PRICE_OPTION"
    result = run_research_tool_action("Price Option", INPUT)
    assert result["status"] == "ok"
    assert result["result"]["payload"]["payload"]["price"] > 0
