from __future__ import annotations

from lib.event_stream import normalize_event
from lib.geo_layers import build_chokepoint_layer, build_event_density_layer, build_global_event_map, build_layered_event_map


def test_geo_layers_return_plotly_or_safe_fallback():
    event = normalize_event({"title": "Hormuz watch", "region": "Middle East", "severity": "high"})
    fig, frame, status = build_global_event_map([event])
    assert status.ok
    assert fig is not None
    assert not frame.empty


def test_chokepoint_layer_no_live_ais_claim():
    fig, frame, status = build_chokepoint_layer()
    assert status.ok
    assert len(frame) >= 8
    assert "No live AIS" in status.warning


def test_density_layer_gap_path():
    fig, frame, status = build_event_density_layer([{"title": "No coordinate"}])
    assert fig is None
    assert not status.ok


def test_layered_event_map_with_route_proxy():
    event = normalize_event({"title": "Suez shipping disruption", "lat": 30.5, "lon": 32.2, "severity": "high"})
    fig, frame, status = build_layered_event_map([event], ["events", "routes", "chokepoints"])
    assert status.ok
    assert fig is not None
