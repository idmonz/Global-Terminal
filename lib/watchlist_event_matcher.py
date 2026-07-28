from __future__ import annotations
from typing import Any
from .osint_entity_matcher import match_events_to_items


def match_events_to_watchlist(events: list[dict[str, Any]], watchlist_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return match_events_to_items(events, watchlist_items, dedupe=True)


def build_event_match_summary(matches: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "match_count": len(matches or []),
        "exact_count": sum(1 for m in matches or [] if "exact" in (m.get("labels") or [])),
        "alias_count": sum(1 for m in matches or [] if "alias" in (m.get("labels") or [])),
        "low_confidence_count": sum(1 for m in matches or [] if m.get("timeline_only")),
        "research_only": True,
    }


def build_watchlist_osint_context(events: list[dict[str, Any]], watchlist_items: list[dict[str, Any]]) -> dict[str, Any]:
    matches = match_events_to_watchlist(events, watchlist_items)
    return {"matches": matches, **build_event_match_summary(matches), "source_confidence_required": True, "no_fake_coordinates": True}


def build_watchlist_event_summary(events: list[dict[str, Any]], watchlist_items: list[dict[str, Any]]) -> dict[str, Any]:
    ctx = build_watchlist_osint_context(events, watchlist_items)
    return {"matched_events": ctx["match_count"], "low_confidence": ctx["low_confidence_count"], "alias": ctx["alias_count"], "exact": ctx["exact_count"]}
