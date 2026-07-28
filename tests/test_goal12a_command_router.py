from lib.command_palette_suggestions import suggest_actions_for_query
from lib.research_command_palette import route_research_command
from lib.terminal_command_router import route_terminal_command
from lib.terminal_function_registry import get_function_definition


def test_terminal_registry_and_router_options_commands():
    assert get_function_definition("OPTIONS LAB")["page"].endswith("24_Options_Quant_Model_Lab.py")
    routed = route_terminal_command("PRICE OPTION")
    assert routed["ok"] is True
    assert routed["research_only"] is True


def test_research_palette_options_commands():
    assert route_research_command("SOLVE IV")["ok"] is True
    suggestions = suggest_actions_for_query("option greeks")
    assert suggestions[0]["command"] == "OPTIONS LAB"
