from __future__ import annotations

from lib.terminal_ui import (
    crypto_terminal_payload,
    energy_terminal_payload,
    provider_health_strip,
    screener_terminal_payload,
    terminal_status_console,
    terminal_ticker_tape,
    workspace_presets,
)


def test_terminal_shell_payloads_cover_goal7_workspaces():
    presets = workspace_presets()
    names = {item["name"] for item in presets}
    assert "Portfolio Quant Lab" in names
    assert "News / OSINT War Room" in names
    assert provider_health_strip()["summary"]["total_providers"] >= 10
    assert terminal_ticker_tape([{"label": "SPY", "value": 500, "delta": 1.2, "freshness": "fresh"}])["items"][0]["label"] == "SPY"
    assert terminal_status_console([{"source": "unit", "status": "ok", "message": "ready"}])["entries"][0]["status"] == "ok"
    assert screener_terminal_payload([{"ticker": "AAA"}])["export_enabled"]
    assert "official liquidation heatmap" in crypto_terminal_payload()["caveat"]
    assert "War_Room" in energy_terminal_payload()["war_room_link"]
