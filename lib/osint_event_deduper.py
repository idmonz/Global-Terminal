from __future__ import annotations
from datetime import datetime
from typing import Any
from .watchlist_alias_registry import normalize_token


def _bucket(ts: Any) -> str:
    text = str(ts or "")[:13]
    return text or "unknown-time"


def event_dedupe_key(event: dict[str, Any]) -> str:
    title = normalize_token(event.get("title") or event.get("headline") or event.get("summary"))[:96]
    source = normalize_token(event.get("source") or event.get("provider"))
    url = normalize_token(event.get("url") or event.get("link"))
    return "|".join([source, url or title, _bucket(event.get("published_at") or event.get("created_at") or event.get("time"))])


def dedupe_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for event in events or []:
        key = event_dedupe_key(event)
        if key in seen:
            continue
        seen.add(key)
        out.append({**event, "dedupe_key": key})
    return out
