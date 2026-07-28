from lib.report_inbox import list_reports
from lib.research_tool_actions import get_research_tool_definition, run_research_tool_action
from lib.research_tool_center import build_research_tool_center_payload
from lib.research_workflow_actions import run_research_workflow_action


def test_goal11e_generate_energy_brief_creates_energy_report_type(tmp_path):
    db = tmp_path / "workspace.db"
    result = run_research_workflow_action("GENERATE_ENERGY_BRIEF", {"title": "Energy context"}, db_path=db)
    assert result["ok"] is True
    assert result["report"]["report_type"] in {"energy_geopolitics", "energy"}
    assert list_reports(include_archived=True, db_path=db)[0]["report_type"] in {"energy_geopolitics", "energy"}


def test_goal11e_every_tool_card_has_action_or_route_only_reason():
    payload = build_research_tool_center_payload()
    tools = [tool for section in payload["sections"] for tool in section["tools"]]
    assert tools
    for tool in tools:
        definition = get_research_tool_definition(tool["tool_name"])
        assert definition is not None
        assert definition.get("workflow_action") or definition.get("route_only_reason")
        text = " ".join(str(v).lower() for v in definition.values())
        assert "broker" not in text
        assert "live execution" not in text


def test_goal11e_new_tool_actions_return_caveated_payloads(tmp_path):
    db = tmp_path / "workspace.db"
    probe = run_research_tool_action("Run Provider Probe", {}, db_path=db)
    data_quality = run_research_tool_action("Inspect Data Quality", {}, db_path=db)
    release = run_research_tool_action("Inspect Release Hygiene", {}, db_path=db)
    assert probe["result"]["action"] == "RUN_PROVIDER_PROBE_DRY_RUN"
    assert data_quality["result"]["action"] == "INSPECT_DATA_QUALITY"
    assert data_quality["result"]["gaps"]
    assert release["result"]["action"] == "INSPECT_RELEASE_HYGIENE"
    assert release["result"]["checklist"]
