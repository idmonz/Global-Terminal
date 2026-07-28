from __future__ import annotations

from lib.layer_registry import build_layer_ui_payload
from lib.terminal_ui import layer_control_payload


def test_layer_ui_payload_shows_available_and_unavailable_layers():
    payload = build_layer_ui_payload(time_range="6h", region="Asia")
    assert payload["time_options"] == ["1h", "6h", "24h", "7d", "30d", "all"]
    assert "Korea" in payload["region_options"]
    assert payload["available_count"] > 0
    assert payload["unavailable_count"] > 0
    assert "clearly marked unavailable" in payload["caveat"]

    terminal_payload = layer_control_payload(search="ais")
    assert terminal_payload["unavailable_layers"]
    assert any("AIS" in layer["label"] for layer in terminal_payload["layers"])
