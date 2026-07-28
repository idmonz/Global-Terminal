from lib.personal_research_workspace import build_personal_research_workspace_payload


def test_personal_research_workspace_payload(tmp_path):
    payload = build_personal_research_workspace_payload(tmp_path/"w.db")
    assert payload["manual_only"] is True
    assert payload["quick_actions"]

