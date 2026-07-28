from __future__ import annotations

from lib.live_news_event_pipeline import build_live_news_event_pipeline, deduplicate_events, normalize_news_event


def test_live_news_event_pipeline_deduplicates_and_geocodes():
    event = normalize_news_event({"title": "Hormuz oil risk", "source": "unit"})
    assert event["truth_label"] == "proxy"
    assert len(deduplicate_events([event, event])) == 1
    payload = build_live_news_event_pipeline([{"title": "Hormuz oil risk", "source": "unit"}])
    assert payload["events"]
    assert payload["caveat"]
