from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lib.data_freshness_engine import classify_freshness, compute_data_freshness, stale_data_warning


def test_freshness_classifies_stale_data():
    fetched = datetime.now(timezone.utc) - timedelta(hours=2)

    result = compute_data_freshness(fetched, stale_after_seconds=60)

    assert result["status"] == "stale"
    assert stale_data_warning("stale")


def test_freshness_handles_missing_age():
    assert classify_freshness(None) == "missing"
