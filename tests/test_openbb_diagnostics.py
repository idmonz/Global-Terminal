from __future__ import annotations

from lib import openbb_bridge
from lib.openbb_diagnostics import build_openbb_diagnostics_table, build_openbb_setup_guide_payload, openbb_provider_key_status


def test_openbb_diagnostics_do_not_require_install(monkeypatch):
    monkeypatch.delitem(openbb_bridge.sys.modules, "openbb", raising=False)
    monkeypatch.setattr(openbb_bridge.importlib.util, "find_spec", lambda name: None)

    table = build_openbb_diagnostics_table()

    assert not table.empty
    assert "native providers remain active" in table.iloc[0]["fallback_path"]


def test_openbb_key_status_hides_secret_values(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "secret")
    keys = openbb_provider_key_status()

    row = keys[keys["env_var"] == "FMP_API_KEY"].iloc[0]
    assert row["configured"] is True or row["configured"] == True
    assert "secret" not in str(keys.to_dict())


def test_openbb_setup_guide_mentions_optional_dependency():
    guide = build_openbb_setup_guide_payload()

    assert "requirements-openbb.txt" in guide["install_command"]
    assert "optional" in guide["dependency_policy"].lower()
