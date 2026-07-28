from __future__ import annotations

from typing import Any


def build_watchlist_action_cards(summary: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    summary = summary or {}
    count = int(summary.get("count", 0) or 0)
    return [
        {"title": "Quick add", "summary": "Add an asset, crypto pair, provider, region, chokepoint, strategy, or topic.", "command": "ADD WATCHLIST", "enabled": True, "research_only": True},
        {"title": "Evaluate alert conditions", "summary": f"Review configured conditions across {count} tracked item(s).", "command": "EVALUATE ALERTS", "enabled": True, "research_only": True},
        {"title": "Generate watchlist brief", "summary": "Create a manual source-labeled research brief from current workspace context.", "command": "GENERATE WATCHLIST BRIEF", "enabled": count > 0, "research_only": True},
    ]
