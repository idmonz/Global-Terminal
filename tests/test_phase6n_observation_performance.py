from __future__ import annotations


def test_phase6n_observation_performance_harness_meets_local_budgets():
    from scripts.benchmark_phase6n import run

    report = run(samples=20)

    assert report["phase"] == "6N"
    assert report["checks"]["plan_25_symbol_equivalent"]["p95_ms"] <= 50
    assert report["checks"]["persist_diff_5_symbols"]["p95_ms"] <= 75
    assert report["checks"]["attention_compose"]["p95_ms"] <= 75
    assert report["checks"]["run_summary_payload"]["bytes"] <= 35_000
    assert report["checks"]["provider_calls_during_triage"]["count"] == 0
    assert report["passed"] is True

