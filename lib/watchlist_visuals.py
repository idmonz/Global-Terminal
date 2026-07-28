from __future__ import annotations

from typing import Any


def build_watchlist_summary_cards(summary: dict[str, Any]) -> list[dict[str, Any]]:
    by_type = summary.get("by_type", {})
    return [
        {"title": "Tracked Items", "value": summary.get("count", 0), "summary": "Local watchlist records across assets, regions, providers, strategies, and report topics."},
        {"title": "Item Types", "value": len(by_type), "summary": ", ".join(f"{k}: {v}" for k, v in sorted(by_type.items())) or "No active types."},
    ]


def build_watchlist_row_badges(item: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"label": str(item.get("item_type") or "item"), "status": "local"},
        {"label": str(item.get("source") or "manual"), "status": "source"},
        {"label": "research-only", "status": "caveat"},
    ]

