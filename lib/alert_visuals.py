from __future__ import annotations
from typing import Any


def build_alert_summary_cards(rules: list[dict[str, Any]], events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    events = events or []
    return [
        {"title": "Active Alert Rules", "value": sum(1 for r in rules if r.get("active")), "summary": "Manual evaluation only; no daemon or email auto-send."},
        {"title": "Triggered Events", "value": sum(1 for e in events if e.get("triggered")), "summary": "Stored alert events with source snapshots where supplied."},
        {"title": "Data Gaps", "value": sum(1 for e in events if "gap" in str(e.get("status", ""))), "summary": "Missing data is skipped rather than converted into false triggers."},
    ]


def build_alert_timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(events, key=lambda e: str(e.get("created_at", "")), reverse=True)


def build_alerts_for_watchlist_item(watch_item_id: str, rules: list[dict[str, Any]], events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"rules": [r for r in rules if r.get("watch_item_id") == watch_item_id], "events": [e for e in (events or []) if e.get("watch_item_id") == watch_item_id]}

