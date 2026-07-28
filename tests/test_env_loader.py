from __future__ import annotations

from lib.env_loader import build_env_status_table, get_masked_env_status, load_project_env


def test_missing_env_does_not_crash(tmp_path):
    status = load_project_env(tmp_path / ".env")
    assert status["exists"] is False
    assert status["loaded"] is False


def test_masked_env_status_never_displays_full_secret(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "abcdef12345")
    status = get_masked_env_status("FRED_API_KEY")
    assert status["configured"] is True
    assert status["masked_value"] == "abc...45"
    assert "abcdef12345" not in str(status)


def test_env_status_table_contains_goal10_keys():
    table = build_env_status_table(["sec_edgar", "nws", "coingecko"])
    assert {"SEC_USER_AGENT", "NWS_USER_AGENT", "COINGECKO_API_KEY"}.issubset(set(table["env_var"]))


def test_env_aliases_and_blank_process_values(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("EIA_API_KEY=real-eia\nOPENSKY_CLIENT_ID=client\nOPENSKY_CLIENT_SECRET=secret\n", encoding="utf-8")
    monkeypatch.setenv("EIA_API_KEY", "")
    monkeypatch.setenv("OPENSKY_CLIENT_ID", "")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "")
    from lib.env_loader import get_env_var, load_project_env

    status = load_project_env(env_file)
    assert "EIA_API_KEY" in status["patched_blank_values"]
    assert get_env_var("EIA_API_KEY") == "real-eia"
    assert get_env_var("OPENSKY_USERNAME") == "client"
    assert get_env_var("OPENSKY_PASSWORD") == "secret"
