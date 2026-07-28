from __future__ import annotations

from lib.provider_health_engine import build_provider_health_summary, compute_provider_health_score


def test_provider_health_summary_counts_statuses():
    results = [{"ok": True, "status": "dry_run"}, {"ok": False, "status": "missing_key"}]
    assert compute_provider_health_score(results) > 0
    assert build_provider_health_summary(results)["gap_count"] == 1
