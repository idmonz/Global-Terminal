from __future__ import annotations

from lib.geospatial_tooltip_engine import build_chokepoint_tooltip, build_event_map_tooltip, build_provider_gap_tooltip, build_vessel_map_tooltip


def test_geospatial_tooltips_show_source_freshness_confidence():
    item = {"label": "Hormuz", "source": "unit", "freshness": "estimated", "confidence": 0.6, "truth_label": "proxy"}
    tooltip = build_event_map_tooltip(item)
    assert "Source: unit" in tooltip
    assert "Freshness: estimated" in tooltip
    assert "Confidence: 0.6" in tooltip
    assert build_vessel_map_tooltip(item)
    assert build_chokepoint_tooltip(item)
    assert build_provider_gap_tooltip(item)
