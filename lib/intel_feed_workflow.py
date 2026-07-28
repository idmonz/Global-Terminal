from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .hotspot_panel import build_hotspot_panel
from .intel_event_actions import build_intel_event_action_cards, run_intel_event_action
from .intel_feed_engine import build_intel_feed
from .layer_catalog_time_controls import build_layer_catalog, filter_layers_by_preset
from .osint_locate_actions import build_locate_action_payload
from .view_preset_filters import build_active_preset_filter_state, filter_events_by_preset, filter_events_by_time_window


def build_intel_workflow_payload(
    events: list[dict[str, Any]] | None = None,
    *,
    preset: str = "Global",
    hours: int | None = None,
    now: datetime | None = None,
    source_snapshot: Any = None,
) -> dict[str, Any]:
    filter_state = build_active_preset_filter_state(preset, hours=hours)
    time_filtered = filter_events_by_time_window(events or [], hours=filter_state["time_window_hours"], now=now)
    preset_filtered = filter_events_by_preset(time_filtered, filter_state["preset"])
    feed = build_intel_feed(preset_filtered, hours=filter_state["time_window_hours"], source_snapshot=source_snapshot, now=now)
    for row, event in zip(feed.get("rows", []), preset_filtered):
        row["action_cards"] = build_intel_event_action_cards(event)
        row["locate_action"] = build_locate_action_payload(event)
        if str(event.get("confidence", "")).lower() in {"low", "low-confidence"}:
            row["status_label"] = "unconfirmed"
        if event.get("location_inferred") or event.get("inferred_location"):
            row["location_label"] = "inferred"
    layers = filter_layers_by_preset(build_layer_catalog(), filter_state.get("layers", []))
    return {
        "preset": filter_state,
        "events": preset_filtered,
        "feed": feed,
        "hotspots": build_hotspot_panel(preset_filtered),
        "layers": layers,
        "no_fake_live_data": True,
        "research_only": True,
    }


__all__ = ["build_intel_workflow_payload", "run_intel_event_action"]
