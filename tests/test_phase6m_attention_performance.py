from __future__ import annotations


def test_phase6m_attention_performance_harness_meets_local_budgets():
    from scripts.benchmark_phase6m import run

    report = run(samples=25)

    assert report["phase"] == "6M"
    assert report["checks"]["compose_100_rows"]["p95_ms"] <= 75
    assert report["checks"]["filter_rank_100_rows"]["p95_ms"] <= 50
    assert report["checks"]["review_mutation"]["p95_ms"] <= 50
    assert report["checks"]["payload"]["bytes"] <= 50_000
    assert report["checks"]["provider_calls"]["count"] == 0
    assert report["passed"] is True
