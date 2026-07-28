from __future__ import annotations

from lib.map_event_clusterer import build_cluster_summary_cards, build_cluster_tooltip, cluster_events_by_proximity, cluster_events_by_region, compute_cluster_severity


def test_map_event_clusterer_summarizes_hotspots():
    events = [{"title": "A", "region": "MENA", "severity": "high", "lat": 1, "lon": 2}, {"title": "B", "region": "MENA", "severity": "watch", "lat": 1.01, "lon": 2.02}]
    clusters = cluster_events_by_region(events)
    assert clusters[0]["count"] == 2
    assert compute_cluster_severity(events) >= 80
    assert build_cluster_tooltip(clusters[0])
    assert cluster_events_by_proximity(events)
    assert build_cluster_summary_cards(clusters)
