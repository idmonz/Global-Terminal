from __future__ import annotations

from lib.event_stream import build_event_feed_cards, build_event_stream, build_event_timeline, normalize_event


def test_event_normalization_schema_and_coordinate_fallback():
    event = normalize_event(
        {
            "title": "Taiwan semiconductor tension",
            "summary": "Policy pressure near Taiwan.",
            "region": "Asia",
            "severity": "high",
            "source": "sample",
        }
    )
    required = {"event_id", "timestamp", "title", "domain", "severity", "confidence", "lat", "lon", "freshness_status", "data_gap"}
    assert required.issubset(event)
    assert event["approximate_location"] is True
    assert "approximate regional centroid" in event["data_gap"]


def test_event_stream_timeline_and_cards():
    events = build_event_stream(news=[{"title": "Iran Hormuz tanker sanctions", "region": "Middle East", "severity": "critical"}])
    assert events
    assert events[0]["severity"] == "critical"
    timeline = build_event_timeline(events)
    assert "event_count" in timeline.columns
    cards = build_event_feed_cards(events)
    assert cards and cards[0]["title"]
