from lib.research_tool_actions import build_tool_missing_data_caveat, get_research_tool_definition, run_research_tool_action, search_research_tools


def test_goal11d_tool_actions_map_to_safe_workflows(tmp_path):
    db = tmp_path / "workspace.db"
    assert get_research_tool_definition("Evaluate Alerts Now")["workflow_action"] == "EVALUATE_ALERTS_NOW"
    assert get_research_tool_definition("Generate Watchlist Brief")["workflow_action"] == "GENERATE_WATCHLIST_BRIEF"
    assert get_research_tool_definition("Export Workspace JSON")["workflow_action"] == "EXPORT_WORKSPACE_JSON"
    result = run_research_tool_action("Generate Watchlist Brief", {"title": "Tool brief"}, db_path=db)
    assert result["status"] == "ok"
    caveat = build_tool_missing_data_caveat(get_research_tool_definition("Generate Provider Health Report"), supplied_data=None)
    assert caveat["missing_data"] is True


def test_goal11d_no_broker_or_market_action_tool_exists():
    text = " ".join(str(tool).lower() for tool in search_research_tools())
    for token in ["broker", "place_order", "order routing", "live execution"]:
        assert token not in text
