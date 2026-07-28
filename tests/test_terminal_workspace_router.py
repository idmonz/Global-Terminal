from __future__ import annotations

from lib.terminal_workspace_router import build_workspace_default_page, build_workspace_registry, route_workspace_payload


def test_workspace_router_returns_expected_workspaces():
    registry = build_workspace_registry()
    labels = {item["label"] for item in registry}
    assert len(registry) == 10
    assert "Global Command Center" in labels
    assert "Korea Market Desk" in labels


def test_workspace_route_payload_adds_context_gaps():
    payload = route_workspace_payload("Portfolio Quant Lab", {"data_gaps": ["factor coverage"]})
    assert "factor coverage" in payload["data_gaps"]
    assert build_workspace_default_page("Portfolio Quant Lab").endswith("16_Portfolio_Quant_Lab.py")
