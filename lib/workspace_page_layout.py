from __future__ import annotations
from pathlib import Path
from typing import Any
from .workspace_summary_engine import build_workspace_summary, build_workspace_summary_cards
from .workspace_quick_actions import build_quick_actions
from .research_os_navigation import build_research_os_nav_cards
from .command_palette_ui import build_command_palette_state
from .source_freshness_strip import build_source_freshness_strip
from .intel_feed_engine import build_intel_feed
from .live_alerts_panel import build_live_alerts_panel
from .view_preset_engine import build_view_presets
from .layer_panel_payload import build_layer_panel_payload
from .hotspot_panel import build_hotspot_panel
from .intelligence_layer_catalog import build_intelligence_layer_catalog


def build_workspace_page_payload(db_path: str | Path | None = None) -> dict[str, Any]:
    summary = build_workspace_summary(db_path)
    counts = summary["counts"]
    empty_states = {"no_watchlist_items": counts["watchlist_items"] == 0, "no_alerts": counts["active_alert_rules"] == 0, "no_reports": counts["reports"] == 0, "no_strategy_commits": counts["strategy_commits"] == 0, "no_provider_snapshots": counts["provider_snapshots"] == 0}
    requires_review = []
    if counts["provider_snapshots"] == 0: requires_review.append("Provider snapshot unavailable.")
    if counts["data_quality_snapshots"] == 0: requires_review.append("Data quality snapshot unavailable.")
    source_rows = [
        {"source": "provider snapshots", "freshness": summary.get("provider_health_snapshot", {}).get("status", "unknown"), "confidence": "local"},
        {"source": "data quality snapshots", "freshness": summary.get("data_quality_snapshot", {}).get("status", "unknown"), "confidence": "local"},
    ]
    events = summary.get("recent_alert_events", []) or []
    return {
        "summary": summary,
        "cards": build_workspace_summary_cards(db_path),
        "source_freshness": build_source_freshness_strip(source_rows, title="Workspace source freshness"),
        "command_palette": build_command_palette_state("BTCUSDT", source_snapshot=source_rows),
        "quick_actions": build_quick_actions(),
        "nav_cards": build_research_os_nav_cards(db_path),
        "intel_feed": build_intel_feed(events, source_snapshot=source_rows),
        "live_alerts": build_live_alerts_panel(events, source_snapshot=source_rows),
        "view_presets": build_view_presets(),
        "layer_panel": build_layer_panel_payload(),
        "hotspot_panel": build_hotspot_panel(events),
        "intelligence_layer_catalog": build_intelligence_layer_catalog(),
        "activity_transcript": summary.get("recent_activity", []),
        "empty_states": empty_states,
        "requires_review": requires_review,
        "raw_payload_available": True,
        "research_only": True,
    }
