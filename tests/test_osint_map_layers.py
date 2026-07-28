from __future__ import annotations

from lib.osint_map_layers import build_enabled_osint_layers, build_osint_map_layer_registry, get_osint_layer


def test_osint_map_layers_have_truth_labels_for_live_boundaries():
    layers = build_osint_map_layer_registry()
    assert get_osint_layer("noaa_accessais")["historical_only"] is True
    assert get_osint_layer("aisstream")["live"] is False
    assert get_osint_layer("nasa_firms")["key_required"] is True
    assert build_enabled_osint_layers()
    assert all("caveat" in layer for layer in layers)
