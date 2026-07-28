from lib.command_palette_suggestions import suggest_actions_for_query
from lib.command_palette_ui import run_command_palette_action
from lib.report_inbox import list_reports
from lib.research_workflow_actions import run_research_workflow_action


def _energy_action(query: str):
    rows = suggest_actions_for_query(query)
    return next(row for row in rows if row["label"] == "Generate Energy Brief")


def test_goal11f_red_sea_and_hormuz_energy_suggestions_route_to_energy_command():
    for query in ["Red Sea", "Hormuz"]:
        action = _energy_action(query)
        assert action["command"] == "GENERATE ENERGY BRIEF"


def test_goal11f_running_energy_palette_action_creates_energy_report_type(tmp_path):
    db = tmp_path / "workspace.db"
    action = _energy_action("Red Sea")
    result = run_command_palette_action(action, query="Red Sea", db_path=db)
    assert result["ok"] is True
    assert result["action"] == "GENERATE_ENERGY_BRIEF"
    reports = list_reports(include_archived=True, db_path=db)
    assert reports[0]["report_type"] == "energy_geopolitics"


def test_goal11f_war_room_and_energy_reports_remain_distinct(tmp_path):
    db = tmp_path / "workspace.db"
    war = run_research_workflow_action("GENERATE_WAR_ROOM_BRIEF", {"region": "Red Sea"}, db_path=db)
    energy = run_research_workflow_action("GENERATE_ENERGY_BRIEF", {"region": "Red Sea"}, db_path=db)
    assert war["report"]["report_type"] == "war_room"
    assert energy["report"]["report_type"] == "energy_geopolitics"
