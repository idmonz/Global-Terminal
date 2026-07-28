from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .view_preset_engine import build_view_presets

_PRESET_KEYWORDS = {
    "Global": [],
    "Americas": ["americas", "north america", "south america", "us", "canada", "mexico"],
    "Europe": ["europe", "eu", "uk", "germany", "france"],
    "MENA": ["mena", "middle east", "north africa", "red sea", "suez", "hormuz", "persian gulf"],
    "East Asia": ["east asia", "china", "japan", "taiwan", "korea"],
    "Korea": ["korea", "south korea", "dprk"],
    "Ukraine / Black Sea": ["ukraine", "black sea", "crimea"],
    "Red Sea / Suez": ["red sea", "suez", "bab el-mandeb", "bab el mandeb"],
    "Hormuz / Persian Gulf": ["hormuz", "persian gulf", "gulf", "iran"],
    "Crypto Stress": ["crypto", "bitcoin", "btc", "ethereum", "eth", "funding", "liquidation"],
    "Energy Routes": ["energy", "oil", "gas", "shipping", "route", "suez", "hormuz", "red sea"],
    "Provider Gaps": ["provider", "missing", "gap", "freshness", "source"],
}


def _event_text(event: dict[str, Any]) -> str:
    return " ".join(str(event.get(k, "")) for k in ["title", "headline", "summary", "description", "region", "location", "tags"]).lower()


def filter_events_by_preset(events: list[dict[str, Any]] | None, preset: str = "Global") -> list[dict[str, Any]]:
    rows = list(events or [])
    keywords = _PRESET_KEYWORDS.get(preset, [])
    if not keywords:
        return rows
    return [event for event in rows if any(keyword in _event_text(event) for keyword in keywords)]


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def filter_events_by_time_window(events: list[dict[str, Any]] | None, *, hours: int = 24, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=int(hours))
    out: list[dict[str, Any]] = []
    for event in events or []:
        ts = _parse_time(event.get("created_at") or event.get("timestamp") or event.get("date"))
        if ts is None or ts >= cutoff:
            out.append(event)
    return out


def build_active_preset_filter_state(preset: str = "Global", *, hours: int | None = None) -> dict[str, Any]:
    active = build_view_presets(preset)["active"]
    return {"preset": active["name"], "layers": active.get("layers", []), "time_window_hours": hours or active.get("time_window_hours", 24), "research_only": True}
