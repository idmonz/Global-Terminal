from __future__ import annotations

from lib.heatmap_visual_theme import build_heatmap_legend, build_heatmap_visual_theme


def test_heatmap_visual_theme_has_legends():
    theme = build_heatmap_visual_theme()
    assert theme["template"] == "plotly_dark"
    assert build_heatmap_legend("provider_health")[0]["label"] == "Fresh"
