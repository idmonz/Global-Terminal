from lib.command_palette_ui import build_command_palette_state
from lib.command_palette_suggestions import build_quick_add_payload, search_research_objects, suggest_actions_for_query
from lib.research_object_resolver import resolve_research_object
from lib.terminal_command_router import route_terminal_command


def test_goal11c_command_palette_suggests_actions_by_object_type():
    assert resolve_research_object("AAPL")["object_type"] == "asset"
    assert any("Financial" in row["label"] for row in suggest_actions_for_query("AAPL"))
    assert resolve_research_object("BTCUSDT")["object_type"] == "crypto"
    assert any("Crypto" in row["label"] for row in suggest_actions_for_query("BTCUSDT"))
    assert resolve_research_object("Red Sea")["object_type"] == "region"
    assert any("War Room" in row["label"] for row in suggest_actions_for_query("Red Sea"))
    assert resolve_research_object("FRED")["object_type"] == "provider"
    assert any("Provider" in row["label"] for row in suggest_actions_for_query("FRED"))
    assert resolve_research_object("Strategy Ensemble #3")["object_type"] == "strategy"
    assert build_quick_add_payload("FRED")["item_type"] == "provider"
    assert search_research_objects("Korea")[0]["actions"]


def test_goal11c_command_palette_blocks_execution_style_commands():
    state = build_command_palette_state("EXECUTE ORDER")
    assert state["suggestions"][0]["enabled"] is False
    assert route_terminal_command("EXECUTE ORDER")["ok"] is False
