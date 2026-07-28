from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_workflow_actions import run_research_workflow_action


def build_intel_event_action_cards(event: dict[str, Any]) -> list[dict[str, Any]]:
    region = event.get("region") or event.get("location") or "Unspecified"
    event_id = event.get("event_id") or event.get("id") or event.get("title") or "event"
    return [
        {"label": "Add region watch", "action": "ADD_WATCHLIST_ITEM", "payload": {"item_type": "region", "display_name": region, "region": region, "tags": ["intel_event"], "metadata": {"event_id": event_id}}, "research_only": True},
        {"label": "Generate War Room Brief", "action": "GENERATE_WAR_ROOM_BRIEF", "payload": {"event_id": event_id, "linked_events": [event_id], "linked_regions": [region], "region": region}, "research_only": True},
        {"label": "Generate Energy Brief", "action": "GENERATE_ENERGY_BRIEF", "payload": {"event_id": event_id, "linked_events": [event_id], "linked_regions": [region], "region": region}, "research_only": True},
        {"label": "Attach to report", "action": "ATTACH_EVENT_TO_REPORT", "payload": {"event_id": event_id, "region": region}, "requires_existing_report": True, "research_only": True},
    ]


def run_intel_event_action(event: dict[str, Any], action: str, payload: dict[str, Any] | None = None, *, db_path: str | Path | None = None) -> dict[str, Any]:
    cards = {card["action"]: card for card in build_intel_event_action_cards(event)}
    if action == "ATTACH_EVENT_TO_REPORT":
        return {"ok": False, "error": "report_selection_required", "research_only": True}
    card = cards.get(action)
    if not card:
        return {"ok": False, "error": "unknown_intel_event_action", "research_only": True}
    merged = {**card.get("payload", {}), **(payload or {})}
    return run_research_workflow_action(action, merged, db_path=db_path)
