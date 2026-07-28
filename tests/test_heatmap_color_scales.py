from __future__ import annotations

from lib.heatmap_color_scales import build_change_color_scale, build_provider_health_color_scale, classify_heatmap_color_bucket, clamp_heatmap_color_value


def test_heatmap_color_scales_classify_modes():
    assert clamp_heatmap_color_value(100, upper=10) == 10
    assert classify_heatmap_color_bucket(4, mode="daily_change") == "strong positive"
    assert classify_heatmap_color_bucket(80, mode="war_room_risk") == "severe risk"
    assert classify_heatmap_color_bucket(status="missing-key") == "key required"
    assert build_change_color_scale()
    assert build_provider_health_color_scale()["historical_only"]
