from __future__ import annotations

from collections import defaultdict
from typing import Any

from .heatmap_layout_engine import build_heatmap_layout
from .live_news_event_pipeline import build_live_news_event_pipeline
from .source_freshness_indicator import build_source_freshness_table


THEME_TERMS = {
    "energy": ("oil", "gas", "energy", "chokepoint", "shipping"),
    "crypto": ("bitcoin", "crypto", "stablecoin", "exchange"),
    "macro": ("rates", "inflation", "fed", "growth", "dollar"),
    "geopolitics": ("war", "conflict", "sanction", "election"),
    "weather": ("storm", "heat", "fire", "earthquake", "weather"),
}


def classify_news_by_theme(item: dict[str, Any]) -> list[str]:
    text = " ".join(str(item.get(key, "")) for key in ("title", "summary", "description")).lower()
    themes = [theme for theme, terms in THEME_TERMS.items() if any(term in text for term in terms)]
    return themes or ["general"]


def link_news_to_assets(item: dict[str, Any]) -> list[str]:
    text = " ".join(str(item.get(key, "")) for key in ("title", "summary", "description")).lower()
    assets = []
    for asset, terms in {"CL=F": ("oil", "brent", "wti"), "XLE": ("energy", "oil"), "BTC": ("bitcoin", "crypto"), "SPY": ("stocks", "equity", "market"), "TLT": ("rates", "treasury")}.items():
        if any(term in text for term in terms):
            assets.append(asset)
    return assets


def link_news_to_regions(item: dict[str, Any]) -> list[str]:
    text = " ".join(str(item.get(key, "")) for key in ("title", "summary", "region", "country")).lower()
    regions = []
    for region in ["Global", "US", "Europe", "MENA", "Asia", "Korea", "Red Sea", "Hormuz"]:
        if region.lower() in text:
            regions.append(region)
    return regions or [str(item.get("region") or "Global")]


def build_news_timeline(events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return sorted(events or [], key=lambda item: str(item.get("timestamp") or ""), reverse=True)


def build_news_heatmap(events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = []
    for event in events or []:
        for theme in event.get("themes", ["general"]):
            rows.append({"name": theme, "event_type": theme, "event_count": 1, "severity_score": {"critical": 95, "high": 80, "medium": 55, "watch": 35, "low": 20}.get(str(event.get("severity", "watch")), 35), "source": event.get("source"), "freshness": event.get("freshness", "estimated")})
    totals: dict[str, dict[str, Any]] = defaultdict(lambda: {"event_count": 0, "severity_score": 0})
    for row in rows:
        item = totals[row["name"]]
        item.update(row)
        item["event_count"] += 1
        item["severity_score"] = max(item["severity_score"], row["severity_score"])
    return build_heatmap_layout(list(totals.values()), title="News Theme Heatmap", size_mode="event_count", color_mode="war_room_risk", group_mode="event_type")


def build_news_impact_cards(events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    cards = []
    for event in (events or [])[:8]:
        cards.append({"title": event.get("title", "News event"), "summary": f"Themes: {', '.join(event.get('themes', []))}; assets: {', '.join(event.get('related_assets', [])) or 'none linked'}.", "severity": event.get("severity", "watch"), "tags": event.get("themes", []), "source": event.get("source", "public feed"), "freshness": event.get("freshness", "estimated")})
    return cards


def build_news_source_freshness_table(statuses: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return build_source_freshness_table(statuses or [])


def build_news_dashboard_payload(news: Any = None, statuses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pipeline = build_live_news_event_pipeline(news, statuses)
    events = []
    for event in pipeline["events"]:
        events.append({**event, "themes": classify_news_by_theme(event), "related_assets": event.get("related_assets") or link_news_to_assets(event), "regions": link_news_to_regions(event)})
    return {
        "events": events,
        "timeline": build_news_timeline(events),
        "theme_filters": sorted({theme for event in events for theme in event["themes"]}),
        "region_filters": sorted({region for event in events for region in event["regions"]}),
        "asset_filters": sorted({asset for event in events for asset in event["related_assets"]}),
        "event_map_preview": [event for event in events if event.get("has_map_point")],
        "duplicate_cluster_note": "Events are deduplicated by event id/title/source.",
        "impact_cards": build_news_impact_cards(events),
        "heatmap": build_news_heatmap(events),
        "source_freshness": build_news_source_freshness_table(statuses),
        "data_gaps": pipeline["data_gaps"],
    }
