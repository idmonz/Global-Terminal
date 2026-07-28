from __future__ import annotations

from lib.source_freshness_indicator import build_data_truth_label, build_source_freshness_indicator, build_source_freshness_table


def test_source_freshness_indicator_truth_labels():
    assert build_data_truth_label(historical_only=True) == "historical-only"
    indicator = build_source_freshness_indicator("NOAA", status="historical-only", confidence=0.7)
    assert indicator["truth_label"] == "historical-only"
    assert build_source_freshness_table([{"source": "GDELT", "status": "fresh"}])[0]["freshness"] == "fresh"
