from __future__ import annotations
from typing import Any
from .watchlist_event_matcher import match_events_to_watchlist, build_event_match_summary


def match_news_to_watchlist(news_items: list[dict[str, Any]], watchlist_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return match_events_to_watchlist(news_items, watchlist_items)


def match_regions_to_watchlist(events: list[dict[str, Any]], watchlist_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    region_items = [i for i in watchlist_items if i.get("item_type") in {"region", "country", "chokepoint", "port"}]
    return match_events_to_watchlist(events, region_items)


def match_chokepoints_to_watchlist(events: list[dict[str, Any]], watchlist_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = [i for i in watchlist_items if i.get("item_type") in {"chokepoint", "port"}]
    return match_events_to_watchlist(events, items)


def match_providers_to_watchlist(provider_snapshots: list[dict[str, Any]], watchlist_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    provider_items = [i for i in watchlist_items if i.get("item_type") == "provider"]
    events = [{"title": p.get("provider_name", p.get("source", "provider")), "summary": p.get("status", ""), "source": "provider_health", "freshness": p.get("freshness", "unknown"), "confidence": p.get("confidence", "unknown"), "provider_snapshot": p} for p in provider_snapshots]
    return match_events_to_watchlist(events, provider_items)


def build_watchlist_osint_context(events: list[dict[str, Any]], watchlist_items: list[dict[str, Any]]) -> dict[str, Any]:
    matches = match_events_to_watchlist(events, watchlist_items)
    return {"matches": matches, **build_event_match_summary(matches), "source_confidence_required": True, "no_fake_coordinates": True}


def build_watchlist_event_summary(events: list[dict[str, Any]], watchlist_items: list[dict[str, Any]]) -> dict[str, Any]:
    ctx = build_watchlist_osint_context(events, watchlist_items)
    return {"matched_events": ctx["match_count"], "low_confidence": ctx["low_confidence_count"], "alias": ctx["alias_count"], "exact": ctx["exact_count"]}
