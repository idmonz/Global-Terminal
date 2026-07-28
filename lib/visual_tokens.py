from __future__ import annotations

from copy import deepcopy
from typing import Any


SPACING_SCALE = {
    "xs": "4px",
    "sm": "8px",
    "md": "12px",
    "lg": "16px",
    "xl": "24px",
    "2xl": "32px",
}

CARD_RADIUS = "8px"
BORDER_STYLE = "1px solid rgba(148, 163, 184, 0.22)"

NEUTRAL_PALETTE = {
    "bg": "#080d14",
    "surface": "#0f1724",
    "surface_raised": "#142033",
    "border": "rgba(148, 163, 184, 0.22)",
    "text": "#e5eefb",
    "muted": "#9aa9bd",
    "subtle": "#64748b",
}

ACCENT_PALETTE = {
    "blue": "#60a5fa",
    "cyan": "#22d3ee",
    "teal": "#2dd4bf",
    "green": "#34d399",
    "amber": "#fbbf24",
    "red": "#fb7185",
    "violet": "#a78bfa",
}

RISK_PALETTE = {
    "low": "#34d399",
    "watch": "#22d3ee",
    "medium": "#fbbf24",
    "elevated": "#fb923c",
    "high": "#fb7185",
    "critical": "#f43f5e",
}

DATA_QUALITY_PALETTE = {
    "live": "#34d399",
    "fresh": "#34d399",
    "aging": "#fbbf24",
    "stale": "#fb923c",
    "unknown": "#94a3b8",
    "proxy": "#60a5fa",
    "estimated": "#22d3ee",
    "historical-only": "#a78bfa",
    "missing-key": "#fb7185",
    "missing": "#fb7185",
    "unavailable": "#94a3b8",
    "inferred location": "#fbbf24",
    "low-confidence geocode": "#fb923c",
}

STATUS_BADGES = {
    key: {"label": key.replace("-", " ").title(), "color": color}
    for key, color in DATA_QUALITY_PALETTE.items()
}

TYPOGRAPHY_SCALE = {
    "eyebrow": {"font_size": "0.72rem", "font_weight": 700},
    "body": {"font_size": "0.86rem", "font_weight": 500},
    "label": {"font_size": "0.75rem", "font_weight": 650},
    "title": {"font_size": "1.08rem", "font_weight": 750},
    "display": {"font_size": "1.68rem", "font_weight": 800},
}

SECTION_HEADER_STYLE = {
    "display": "flex",
    "justify_content": "space-between",
    "gap": SPACING_SCALE["md"],
    "border_bottom": BORDER_STYLE,
    "padding_bottom": SPACING_SCALE["sm"],
}

METRIC_CARD_STYLE = {
    "background": NEUTRAL_PALETTE["surface"],
    "border": BORDER_STYLE,
    "border_radius": CARD_RADIUS,
    "padding": SPACING_SCALE["md"],
}

COMPACT_TABLE_STYLE = {
    "row_height": "34px",
    "header_background": NEUTRAL_PALETTE["surface_raised"],
    "border": BORDER_STYLE,
}

CHART_CARD_STYLE = {
    **METRIC_CARD_STYLE,
    "min_height": "320px",
}


def get_visual_tokens() -> dict[str, Any]:
    return {
        "spacing": deepcopy(SPACING_SCALE),
        "card_radius": CARD_RADIUS,
        "border_style": BORDER_STYLE,
        "neutral": deepcopy(NEUTRAL_PALETTE),
        "accent": deepcopy(ACCENT_PALETTE),
        "risk": deepcopy(RISK_PALETTE),
        "data_quality": deepcopy(DATA_QUALITY_PALETTE),
        "status_badges": deepcopy(STATUS_BADGES),
        "typography": deepcopy(TYPOGRAPHY_SCALE),
        "section_header": deepcopy(SECTION_HEADER_STYLE),
        "metric_card": deepcopy(METRIC_CARD_STYLE),
        "compact_table": deepcopy(COMPACT_TABLE_STYLE),
        "chart_card": deepcopy(CHART_CARD_STYLE),
    }


def status_badge_tokens(status: str | None) -> dict[str, str]:
    key = str(status or "unknown").lower().replace("_", "-")
    item = STATUS_BADGES.get(key, STATUS_BADGES["unknown"])
    return {"status": key, "label": item["label"], "color": item["color"]}


def risk_tone(severity: str | None) -> dict[str, str]:
    key = str(severity or "watch").lower().replace("_", "-")
    color = RISK_PALETTE.get(key, RISK_PALETTE["watch"])
    return {"severity": key, "color": color}


def data_quality_tone(status: str | None) -> dict[str, str]:
    return status_badge_tokens(status)


def build_token_css(namespace: str = ".gmt") -> str:
    ns = namespace.strip() or ".gmt"
    return f"""
<style>
{ns}-shell {{
  background: {NEUTRAL_PALETTE["bg"]};
  color: {NEUTRAL_PALETTE["text"]};
}}
{ns}-card {{
  background: {NEUTRAL_PALETTE["surface"]};
  border: {BORDER_STYLE};
  border-radius: {CARD_RADIUS};
  padding: {SPACING_SCALE["md"]};
}}
{ns}-muted {{ color: {NEUTRAL_PALETTE["muted"]}; }}
{ns}-chip {{
  display: inline-flex;
  gap: 6px;
  align-items: center;
  border: {BORDER_STYLE};
  border-radius: 999px;
  padding: 3px 8px;
  font-size: {TYPOGRAPHY_SCALE["label"]["font_size"]};
}}
</style>
""".strip()
