from datetime import datetime, timezone

from lib.intel_feed_engine import build_event_time_window_filter, build_intel_feed
from lib.intel_feed_workflow import build_intel_workflow_payload


def test_goal12e_build_intel_feed_includes_archived_events_by_default():
    events = [
        {"title": "Archived supplied event", "created_at": "2024-01-01T00:00:00+00:00", "confidence": "high", "source": "fixture"},
        {"title": "Low confidence event", "created_at": "2024-01-02T00:00:00+00:00", "confidence": "low", "source": "fixture"},
    ]
    feed = build_intel_feed(events)
    assert [row["title"] for row in feed["rows"]] == ["Archived supplied event", "Low confidence event"]
    assert feed["rows"][1]["status_label"] == "unconfirmed"
    assert feed["no_fake_live_data"] is True


def test_goal12e_explicit_time_window_filter_remains_available():
    events = [
        {"title": "old", "created_at": "2026-06-10T00:00:00+00:00"},
        {"title": "fresh", "created_at": "2026-06-14T12:00:00+00:00"},
    ]
    out = build_event_time_window_filter(events, hours=24, now=datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc))
    assert out["count"] == 1
    assert out["events"][0]["title"] == "fresh"


def test_goal12e_intel_workflow_payload_still_applies_explicit_time_window():
    events = [
        {"title": "old red sea", "region": "Red Sea", "created_at": "2026-06-10T00:00:00+00:00"},
        {"title": "fresh red sea", "region": "Red Sea", "created_at": "2026-06-14T12:00:00+00:00"},
    ]
    payload = build_intel_workflow_payload(events, preset="Red Sea / Suez", hours=24, now=datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc))
    assert [row["title"] for row in payload["feed"]["rows"]] == ["fresh red sea"]
    assert payload["no_fake_live_data"] is True
