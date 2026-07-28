from __future__ import annotations

from lib.intelligence_scoring import build_hotspot_leaderboard, build_intelligence_watchpoints, compute_event_severity, compute_signal_convergence


def test_signal_scores_are_bounded():
    convergence = compute_signal_convergence(news_severity="high", source_count=3, market_move=2.5, volatility_move=5, related_assets=4, data_freshness="fresh")
    assert 0 <= convergence["score"] <= 100
    event_score = compute_event_severity({"severity": "critical", "confidence": 0.8, "related_tickers": ["CL=F"], "freshness_status": "fresh"})
    assert 0 <= event_score["score"] <= 100


def test_hotspot_leaderboard_and_watchpoints():
    events = [{"title": "Iran Hormuz tanker sanctions", "region": "Middle East", "severity": "high", "related_tickers": ["CL=F", "BZ=F"], "source": "sample"}]
    leaderboard = build_hotspot_leaderboard(events)
    assert not leaderboard.empty
    assert leaderboard["score"].between(0, 100).all()
    watchpoints = build_intelligence_watchpoints(events)
    assert watchpoints and "not instructions" in watchpoints[0]["caveat"]
