from __future__ import annotations
from typing import Any
from .watchlist_alias_registry import build_watchlist_alias_terms, normalize_token, aliases_for
from .osint_confidence_scoring import score_match, confidence_label
from .osint_event_deduper import dedupe_events


def event_terms(event: dict[str, Any]) -> set[str]:
    fields = [event.get("title"), event.get("headline"), event.get("summary"), event.get("description"), event.get("region"), event.get("country"), event.get("source"), event.get("provider"), event.get("category"), event.get("theme")]
    fields += list(event.get("tags") or [])
    text = " ".join(str(x or "") for x in fields).lower()
    raw = {normalize_token(x) for x in fields if normalize_token(x)}
    expanded = set(raw)
    for term in list(raw):
        expanded.update(aliases_for(term))
    # Add aliases whose words are found inside the event text.
    for term in list(expanded):
        if term and term in text:
            expanded.add(term)
    return {x for x in expanded if x}


def match_event_to_item(event: dict[str, Any], item: dict[str, Any]) -> dict[str, Any] | None:
    item_terms = build_watchlist_alias_terms(item)
    e_terms = event_terms(event)
    dims: set[str] = set()
    symbol = normalize_token(item.get("symbol"))
    if symbol and symbol in e_terms.union({normalize_token(event.get("title")), normalize_token(event.get("summary"))}):
        dims.add("exact_symbol")
    if item_terms & e_terms:
        dims.add("alias")
    if normalize_token(item.get("region")) and normalize_token(item.get("region")) in e_terms:
        dims.add("region")
    if normalize_token(item.get("country")) and normalize_token(item.get("country")) in e_terms:
        dims.add("country")
    if set(normalize_token(t) for t in item.get("tags") or []) & e_terms:
        dims.add("tag")
    if normalize_token(item.get("asset_class")) in e_terms or normalize_token(item.get("item_type")) in e_terms:
        dims.add("theme")
    if not dims:
        # weak text fallback for symbol/name substrings
        blob = " ".join(e_terms)
        for term in item_terms:
            if len(term) >= 4 and term in blob:
                dims.add("theme")
                break
    if not dims:
        return None
    score, primary = score_match(dims)
    label = confidence_label(score)
    return {
        "item_id": item.get("item_id"),
        "symbol": item.get("symbol"),
        "display_name": item.get("display_name"),
        "event": event,
        "confidence_score": score,
        "confidence": score,
        "match_type": primary,
        "labels": [label] + sorted(dims),
        "timeline_only": score < 0.5,
        "inferred": score < 0.9,
        "source": event.get("source") or event.get("provider") or "supplied-events",
        "freshness": event.get("freshness", "unknown"),
    }


def match_events_to_items(events: list[dict[str, Any]], items: list[dict[str, Any]], *, dedupe: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_events = dedupe_events(events or []) if dedupe else (events or [])
    for event in source_events:
        for item in items or []:
            match = match_event_to_item(event, item)
            if match:
                rows.append(match)
    return sorted(rows, key=lambda r: r.get("confidence_score", 0), reverse=True)
