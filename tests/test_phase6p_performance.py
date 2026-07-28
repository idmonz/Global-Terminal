from __future__ import annotations


def test_phase6p_account_continuity_performance_harness_meets_local_budgets():
    from scripts.benchmark_phase6p import run

    report = run(samples=15)
    assert report["checks"]["capture_100_rows"]["p95_ms"] <= 100
    assert report["checks"]["restore_100_rows"]["p95_ms"] <= 175
    assert report["checks"]["continuity_status"]["p95_ms"] <= 50
    assert report["checks"]["account_bundle"]["rows"] == 100
    assert report["checks"]["account_bundle"]["bytes"] <= 512_000
    assert report["checks"]["restore_integrity"]["provider_calls"] == 0
    assert report["passed"] is True
