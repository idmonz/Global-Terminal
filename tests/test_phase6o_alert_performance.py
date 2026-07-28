from scripts.benchmark_phase6o import run_benchmark


def test_phase6o_bounded_five_symbol_path_meets_local_p95_and_payload_gates():
    result = run_benchmark(samples=50)

    assert result["symbol_count"] == 5
    assert result["due_plan_p95_ms"] < 75
    assert result["evaluation_p95_ms"] < 75
    assert result["read_p95_ms"] < 75
    assert result["payload_bytes"] < 100_000
    assert result["provider_call_count"] == 0
    assert result["passed"] is True
