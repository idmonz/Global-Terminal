from __future__ import annotations

from lib.energy_geopolitics_map import build_energy_geopolitics_map_payload, build_energy_risk_summary_cards, build_energy_shipping_layer, build_oil_chokepoint_layer


def test_energy_geopolitics_map_labels_shipping_as_proxy():
    payload = build_energy_geopolitics_map_payload()
    assert payload["chokepoint_layer"]
    assert payload["shipping_layer"]["live"] is False
    assert payload["data_quality"][0]["status"] == "historical-only"
    assert build_oil_chokepoint_layer()
    assert build_energy_shipping_layer()["status"] == "proxy"
    assert build_energy_risk_summary_cards()
