from lib.research_command_palette import build_research_command_palette, route_research_command, search_research_commands


def test_research_command_palette():
    assert route_research_command("WORKSPACE")["page"] == "pages/19_Research_Workspace.py"
    assert route_research_command("BTCUSDT WATCH")["ok"] is True
    assert search_research_commands("REPORT")
    assert build_research_command_palette()

