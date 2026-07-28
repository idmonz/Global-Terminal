from __future__ import annotations

from lib.intel_scorecard_engine import build_scorecard_table, build_security_scorecard, summarize_scorecard


def test_intel_scorecard_research_labels_only():
    scorecard = build_security_scorecard("AAPL", {"change_pct": 2, "momentum_pct": 4, "pe": 25})
    assert scorecard["label"] in {"constructive", "deteriorating", "mixed"}
    assert len(build_scorecard_table(scorecard)) >= 5
    assert "scorecard" in summarize_scorecard(scorecard)
