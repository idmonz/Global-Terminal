from __future__ import annotations

from typing import Any

from .heatmap_color_scales import build_change_color_scale, build_event_severity_color_scale, build_provider_health_color_scale, build_risk_color_scale


def build_heatmap_visual_theme() -> dict[str, Any]:
    return {
        "template": "plotly_dark",
        "background": "#080d14",
        "paper_bgcolor": "#080d14",
        "plot_bgcolor": "#080d14",
        "font_color": "#e5eefb",
        "border_color": "rgba(148, 163, 184, 0.22)",
        "tile_border": "rgba(15, 23, 42, 0.8)",
        "colors": {
            "change": build_change_color_scale(),
            "risk": build_risk_color_scale(),
            "provider": build_provider_health_color_scale(),
            "event": build_event_severity_color_scale(),
        },
    }


def build_heatmap_legend(mode: str = "daily_change") -> list[dict[str, str]]:
    if "risk" in mode or "severity" in mode:
        return [{"label": "Low", "color": "#164e63"}, {"label": "Elevated", "color": "#f59e0b"}, {"label": "Severe", "color": "#ef4444"}]
    if "provider" in mode or "quality" in mode or "freshness" in mode:
        return [{"label": "Fresh", "color": "#22c55e"}, {"label": "Proxy", "color": "#38bdf8"}, {"label": "Missing", "color": "#ef4444"}]
    return [{"label": "Negative", "color": "#fb7185"}, {"label": "Neutral", "color": "#334155"}, {"label": "Positive", "color": "#4ade80"}]


def apply_heatmap_layout_theme(fig: Any, *, title: str | None = None) -> Any:
    if fig is not None and hasattr(fig, "update_layout"):
        fig.update_layout(template="plotly_dark", paper_bgcolor="#080d14", plot_bgcolor="#080d14", font_color="#e5eefb", title=title)
    return fig
