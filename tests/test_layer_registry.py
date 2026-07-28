from __future__ import annotations

from lib.layer_registry import REQUIRED_LAYER_FIELDS, build_layer_registry, filter_layers_by_availability, layer_status_table, validate_layer_payload


def test_layer_registry_schema_and_status_table():
    layers = build_layer_registry()
    assert layers
    assert all(set(REQUIRED_LAYER_FIELDS).issubset(layer) for layer in layers)
    valid, issues = validate_layer_payload(layers)
    assert valid, issues
    table = layer_status_table(layers)
    assert set(REQUIRED_LAYER_FIELDS).issubset(table.columns)


def test_unavailable_layers_are_marked_unavailable_or_optional():
    unavailable = filter_layers_by_availability(False)
    assert unavailable
    assert all(layer["is_available"] is False for layer in unavailable)
    assert any(layer["is_optional"] for layer in unavailable)
    assert any("AIS" in layer["caveat"] or "vessel" in layer["caveat"] for layer in unavailable)
