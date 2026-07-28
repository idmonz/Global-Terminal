from __future__ import annotations

from lib.oil_flows import build_chokepoint_registry, compute_oil_scenario_matrix, compute_shipping_disruption_proxy


def test_chokepoint_registry_contains_required_names():
    registry = build_chokepoint_registry()
    names = set(registry["name"])
    assert {"Strait of Hormuz", "Suez Canal", "Bab el-Mandeb", "Strait of Malacca", "Panama Canal", "Bosphorus", "Dardanelles", "Strait of Gibraltar"}.issubset(names)


def test_shipping_proxy_estimated_label():
    payload, status = compute_shipping_disruption_proxy()
    assert status.ok
    assert status.is_estimated
    assert "Live AIS unavailable" in payload["warning"]


def test_oil_scenario_matrix_four_rows():
    frame, status = compute_oil_scenario_matrix()
    assert status.ok
    assert len(frame) == 4

