from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lib.refresh_state import build_refresh_control_payload, build_refresh_state, classify_refresh_state, should_refresh


def test_refresh_state_classifies_fresh_and_stale():
    now = datetime(2026, 6, 11, tzinfo=timezone.utc)
    assert classify_refresh_state(now - timedelta(seconds=10), ttl_seconds=60, now=now) == "fresh"
    assert classify_refresh_state(now - timedelta(seconds=500), ttl_seconds=60, now=now) == "stale"
    assert should_refresh(None)
    assert build_refresh_state(now, now=now)["status"] == "fresh"
    assert build_refresh_control_payload(now)["label"] == "Refresh"
