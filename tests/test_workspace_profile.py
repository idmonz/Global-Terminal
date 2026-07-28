from lib.workspace_profile import get_or_create_workspace_profile, save_workspace_profile


def test_workspace_profile_create_load(tmp_path):
    db = tmp_path / "p.db"
    profile = get_or_create_workspace_profile(db)
    assert profile["profile_id"] == "default"
    updated = save_workspace_profile({"profile_id": "default", "display_name": "Researcher"}, db)
    assert updated["display_name"] == "Researcher"

