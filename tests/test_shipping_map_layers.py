from __future__ import annotations

from lib.shipping_map_layers import build_historical_ais_layer, build_port_layer, build_shipping_chokepoint_layers, build_shipping_data_quality_report


def test_shipping_map_layers_do_not_claim_live_data():
    assert build_shipping_chokepoint_layers()[0]["truth_label"] == "proxy"
    assert build_historical_ais_layer([{"name": "Archive row"}])[0]["freshness"] == "historical-only"
    assert build_port_layer([{"name": "Busan"}])[0]["truth_label"] == "proxy"
    assert all(row["live"] is False for row in build_shipping_data_quality_report())
