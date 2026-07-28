from __future__ import annotations

from hashlib import sha1
from typing import Any

from .world_event_geocoder import build_geocoded_events


def normalize_news_event(item: dict[str, Any]) -> dict[str, Any]:
    title = str(item.get("title") or item.get("headline") or "Untitled event")
    source = str(item.get("source") or item.get("provider") or "public feed")
    event_id = item.get("event_id") or sha1(f"{title}|{source}".encode("utf-8")).hexdigest()[:12]
    severity = str(item.get("severity") or "watch").lower()
    source_status = str(item.get("source_status") or item.get("freshness") or "estimated").lower()
    truth_label = item.get("truth_label") or ("source" if item.get("provider") and source_status in {"fresh", "stale"} else "proxy")
    return {
        "event_id": event_id,
        "title": title,
        "summary": item.get("summary") or item.get("description") or "",
        "source": source,
        "source_url": item.get("source_url") or item.get("url") or item.get("link") or "",
        "provider": item.get("provider") or "public_feed",
        "fetched_at": item.get("fetched_at"),
        "source_status": source_status,
        "timestamp": item.get("timestamp") or item.get("published_at") or item.get("checked_at"),
        "severity": severity,
        "event_type": item.get("event_type") or item.get("theme") or "news",
        "region": item.get("region") or item.get("country") or "Global",
        "related_assets": item.get("related_assets") or item.get("asset_tags") or [],
        "confidence": item.get("confidence", 0.55),
        "freshness": item.get("freshness", "estimated"),
        "truth_label": truth_label,
        "lat": item.get("lat"),
        "lon": item.get("lon"),
        "coordinate_method": item.get("coordinate_method"),
        "data_gap": item.get("data_gap"),
        "caveat": item.get("caveat"),
    }


def deduplicate_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output = []
    for event in events:
        key = str(event.get("event_id") or event.get("title")).lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(event)
    return output


def build_live_news_event_pipeline(news: Any = None, statuses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if hasattr(news, "to_dict"):
        records = news.to_dict(orient="records")
    else:
        records = list(news or [])
    normalized = deduplicate_events([normalize_news_event(dict(item)) for item in records])
    geocoded = build_geocoded_events(normalized)
    return {
        "events": geocoded,
        "map_events": [event for event in geocoded if event["has_map_point"]],
        "timeline": sorted(geocoded, key=lambda item: str(item.get("timestamp") or ""), reverse=True),
        "source_statuses": statuses or [],
        "data_gaps": ["News geocoding may be inferred from region-level text."],
        "caveat": "Public news feeds can be noisy, duplicated, delayed, or missing coordinates.",
    }


def build_news_event_stream(news: Any = None, statuses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Compatibility wrapper for Goal 10B/11 canonical guard checks."""
    return build_live_news_event_pipeline(news, statuses)
