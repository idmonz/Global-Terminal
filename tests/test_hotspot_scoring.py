from __future__ import annotations

from lib.hotspot_scoring import (
    build_hotspot_leaderboard,
    compute_asset_hotspot_score,
    compute_chokepoint_hotspot_score,
    compute_region_hotspot_score,
)


def test_hotspot_scores_are_bounded_and_heuristic():
    region = compute_region_hotspot_score({"region": "Middle East", "headline_count": 4, "high_count": 2, "score": 65})
    asset = compute_asset_hotspot_score({"ticker": "WTI", "return_abs_pct": 3, "realized_volatility_pct": 42, "news_severity_score": 70})
    chokepoint = compute_chokepoint_hotspot_score({"name": "Strait of Hormuz", "risk_proxy": "elevated", "related_headlines": 3})

    for score in [region, asset, chokepoint]:
        assert 0 <= score["score"] <= 100
        assert score["is_estimated"]
        assert "heuristic" in score["method"]

    leaderboard = build_hotspot_leaderboard([region], [asset], [chokepoint])
    assert len(leaderboard) == 3
    assert leaderboard.iloc[0]["score"] >= leaderboard.iloc[-1]["score"]
