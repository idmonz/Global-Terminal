from __future__ import annotations

import pandas as pd

from lib.map_viz import build_chokepoint_map, build_energy_route_map_proxy, build_event_map


def test_chokepoint_map_schema():
    fig, frame, status = build_chokepoint_map()
    assert status.ok
    assert len(frame) >= 8
    assert {"name", "lat", "lon", "risk_proxy", "source_status"}.issubset(frame.columns)


def test_event_map_coordinate_gap_path():
    fig, frame, status = build_event_map(pd.DataFrame([{"title": "No coordinate event"}]))
    assert fig is None
    assert not status.ok
    assert "coordinates" in status.error


def test_energy_route_proxy_labels_no_live_flow():
    fig, routes, status = build_energy_route_map_proxy()
    assert status.ok
    assert status.is_estimated
    assert "AIS unavailable" in status.warning
