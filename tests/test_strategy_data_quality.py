from __future__ import annotations

from lib.strategy_data_quality import compute_strategy_data_quality_score, detect_strategy_data_gaps


def test_strategy_data_quality_detects_gaps():
    payload = {"factors": {"value": None}, "sample_length": 100, "missing_pct": 8, "proxy_dependence": True}
    score = compute_strategy_data_quality_score(payload)
    gaps = detect_strategy_data_gaps(payload)
    assert score["label"] == "limited"
    assert len(gaps) >= 3
