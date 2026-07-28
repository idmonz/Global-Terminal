from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
from typing import Iterable

import pandas as pd
import requests
import xml.etree.ElementTree as ET

from .config import get_settings
from .env_loader import get_env_var
from .data_status import error_result, ok_result
from .feed_registry import default_rss_feed_urls, feed_definition_for_url


NEWS_KEYWORDS = [
    "oil",
    "crude",
    "Brent",
    "WTI",
    "refinery",
    "pipeline",
    "tanker",
    "Hormuz",
    "Suez",
    "OPEC",
    "Russia",
    "Iran",
    "Venezuela",
    "Libya",
    "sanctions",
    "inventory",
    "export",
    "import",
    "storage",
    "Cushing",
]

CLASSIFICATION_KEYWORDS = {
    "oil_supply": ["supply", "production", "export", "OPEC"],
    "oil_demand": ["demand", "consumption", "product supplied"],
    "refinery": ["refinery", "refining", "outage"],
    "pipeline": ["pipeline"],
    "tanker": ["tanker", "shipping", "vessel"],
    "chokepoint": ["Hormuz", "Suez", "Bab el-Mandeb", "Malacca", "Red Sea"],
    "sanctions": ["sanction", "embargo"],
    "war_conflict": ["war", "conflict", "attack", "missile"],
    "opec_policy": ["OPEC", "quota", "cut"],
    "inventory": ["inventory", "stocks", "Cushing"],
    "macro": ["dollar", "rates", "inflation", "growth"],
}

REGION_KEYWORDS = {
    "Middle East": ["Hormuz", "Iran", "Saudi", "OPEC", "Persian Gulf"],
    "Red Sea": ["Bab el-Mandeb", "Red Sea", "Yemen", "Houthi", "Suez"],
    "Europe": ["Europe", "EU", "Germany", "Brent", "North Sea"],
    "Asia": ["China", "Japan", "Korea", "Malacca", "Taiwan", "Singapore"],
    "Americas": ["US", "United States", "Cushing", "Panama", "Venezuela", "Mexico"],
}

ASSET_KEYWORDS = {
    "oil": ["oil", "crude", "Brent", "WTI", "OPEC", "refinery", "Cushing"],
    "energy": ["energy", "natural gas", "LNG", "pipeline", "power"],
    "shipping": ["tanker", "shipping", "vessel", "canal", "strait"],
    "equity": ["stocks", "equity", "shares", "earnings"],
    "crypto": ["bitcoin", "crypto", "stablecoin", "exchange"],
    "rates": ["rates", "bond", "treasury", "yield"],
}

LOCATION_KEYWORDS = {
    "Hormuz": {"lat": 26.5667, "lon": 56.25, "location": "Strait of Hormuz"},
    "Suez": {"lat": 30.5852, "lon": 32.2654, "location": "Suez Canal"},
    "Bab el-Mandeb": {"lat": 12.5833, "lon": 43.3333, "location": "Bab el-Mandeb"},
    "Malacca": {"lat": 2.5, "lon": 101.0, "location": "Strait of Malacca"},
    "Panama": {"lat": 9.08, "lon": -79.68, "location": "Panama Canal"},
    "Bosphorus": {"lat": 41.12, "lon": 29.07, "location": "Bosphorus"},
    "Dardanelles": {"lat": 40.15, "lon": 26.4, "location": "Dardanelles"},
    "Gibraltar": {"lat": 35.96, "lon": -5.55, "location": "Strait of Gibraltar"},
}


DEFAULT_RSS_FEEDS = default_rss_feed_urls()


def _request_headers() -> dict[str, str]:
    user_agent = (
        get_env_var("NEWS_FEED_USER_AGENT")
        or get_env_var("SEC_USER_AGENT")
        or get_env_var("NWS_USER_AGENT")
        or "GlobalMarketAnalystTerminal/1.0 research dashboard"
    )
    return {"User-Agent": user_agent, "Accept": "application/json, application/xml, text/xml;q=0.9, */*;q=0.8"}


def _parse_datetime(value: object):
    if value is None:
        return pd.NaT
    try:
        parsed = parsedate_to_datetime(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return pd.Timestamp(parsed).tz_convert("UTC")
    except Exception:
        return pd.to_datetime(value, utc=True, errors="coerce")


def build_oil_news_query(extra_keywords: Iterable[str] | None = None) -> str:
    keywords = list(NEWS_KEYWORDS)
    if extra_keywords:
        keywords.extend(extra_keywords)
    deduped = list(dict.fromkeys(keywords))
    return " OR ".join(deduped)


def fetch_gdelt_news(query: str | None = None, max_records: int = 20) -> tuple[pd.DataFrame, object]:
    if not get_settings().gdelt_enabled:
        return pd.DataFrame(), error_result(source="GDELT", provider="gdelt", error="GDELT_ENABLED is false.")
    query = query or build_oil_news_query()
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {"query": query, "mode": "artlist", "format": "json", "maxrecords": max_records, "sort": "hybridrel"}
    try:
        response = requests.get(url, params=params, headers=_request_headers(), timeout=15)
        if response.status_code == 429:
            return pd.DataFrame(), error_result(
                source="GDELT DOC",
                provider="gdelt",
                error="GDELT rate limited the request (HTTP 429).",
                warning="RSS feeds remain available when reachable.",
            )
        if response.status_code in {401, 403}:
            return pd.DataFrame(), error_result(
                source="GDELT DOC",
                provider="gdelt",
                error=f"GDELT rejected the request (HTTP {response.status_code}).",
            )
        response.raise_for_status()
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return pd.DataFrame(), error_result(
                source="GDELT DOC",
                provider="gdelt",
                error="GDELT returned a non-JSON response.",
                warning="This usually means the public endpoint throttled or served an HTML error page.",
            )
        rows = payload.get("articles", []) if isinstance(payload, dict) else []
        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame, error_result(source="GDELT DOC", provider="gdelt", error="No GDELT articles returned.")
        frame = frame.rename(columns={"seendate": "published_at", "domain": "source"})
        frame["credibility"] = "secondary"
        frame["classification"] = frame.apply(lambda row: classify_geopolitical_news(row.to_dict()), axis=1)
        return dedupe_news_items(frame), ok_result(frame, source="GDELT DOC", provider="gdelt", coverage=f"{len(frame)} articles")
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        message = f"GDELT request failed (HTTP {status_code})." if status_code else "GDELT request failed."
        return pd.DataFrame(), error_result(source="GDELT DOC", provider="gdelt", error=message)
    except Exception as exc:
        return pd.DataFrame(), error_result(source="GDELT DOC", provider="gdelt", error=f"GDELT request failed: {exc.__class__.__name__}")


def fetch_public_rss_news(urls: list[str] | None = None) -> tuple[pd.DataFrame, object]:
    urls = urls or DEFAULT_RSS_FEEDS
    rows: list[dict] = []
    errors: list[str] = []
    for url in urls:
        feed = feed_definition_for_url(url) or {}
        source_label = feed.get("label") or url
        try:
            response = requests.get(url, headers=_request_headers(), timeout=12)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            atom_entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items[:20]:
                title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                published = item.findtext("pubDate") or item.findtext("date") or ""
                summary = item.findtext("description") or item.findtext("summary") or ""
                rows.append(
                    {
                        "title": title,
                        "url": link,
                        "published_at": published,
                        "summary": summary,
                        "source": source_label,
                        "source_url": link or url,
                        "feed_id": feed.get("feed_id", ""),
                        "feed_category": feed.get("category", ""),
                        "source_type": feed.get("source_type", "rss"),
                        "tier": feed.get("tier", ""),
                        "source_risk": feed.get("source_risk", ""),
                        "caveat": feed.get("caveat", "Public RSS feeds can lag, duplicate, or revise stories."),
                        "credibility": feed.get("credibility") or _credibility_from_url(url),
                    }
                )
            for item in atom_entries[:20]:
                link_node = item.find("{http://www.w3.org/2005/Atom}link")
                link = link_node.attrib.get("href", "") if link_node is not None else ""
                rows.append(
                    {
                        "title": item.findtext("{http://www.w3.org/2005/Atom}title") or "",
                        "url": link,
                        "published_at": item.findtext("{http://www.w3.org/2005/Atom}updated") or item.findtext("{http://www.w3.org/2005/Atom}published") or "",
                        "summary": item.findtext("{http://www.w3.org/2005/Atom}summary") or "",
                        "source": source_label,
                        "source_url": link or url,
                        "feed_id": feed.get("feed_id", ""),
                        "feed_category": feed.get("category", ""),
                        "source_type": feed.get("source_type", "rss"),
                        "tier": feed.get("tier", ""),
                        "source_risk": feed.get("source_risk", ""),
                        "caveat": feed.get("caveat", "Public RSS feeds can lag, duplicate, or revise stories."),
                        "credibility": feed.get("credibility") or _credibility_from_url(url),
                    }
                )
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["classification"] = frame.apply(lambda row: classify_geopolitical_news(row.to_dict()), axis=1)
        frame = dedupe_news_items(frame)
        return frame, ok_result(frame, source="public RSS feeds", provider="rss", warning="; ".join(errors[:3]) if errors else None, coverage=f"{len(frame)} items")
    return frame, error_result(source="public RSS feeds", provider="rss", error="; ".join(errors) or "No RSS rows returned.")


def fetch_newsapi_news(query: str | None = None, max_records: int = 20) -> tuple[pd.DataFrame, object]:
    settings = get_settings()
    if not settings.newsapi_key:
        return pd.DataFrame(), error_result(
            source="NewsAPI",
            provider="newsapi",
            error="NEWSAPI_KEY is not configured.",
            is_paid_required=True,
        )
    params = {
        "q": query or build_oil_news_query(["markets", "geopolitics"]),
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": min(max_records, 100),
        "apiKey": settings.newsapi_key,
    }
    try:
        response = requests.get("https://newsapi.org/v2/everything", params=params, headers=_request_headers(), timeout=15)
        if response.status_code in {401, 403}:
            return pd.DataFrame(), error_result(source="NewsAPI", provider="newsapi", error=f"NewsAPI rejected the request (HTTP {response.status_code}).")
        if response.status_code == 429:
            return pd.DataFrame(), error_result(source="NewsAPI", provider="newsapi", error="NewsAPI rate limited the request (HTTP 429).")
        response.raise_for_status()
        payload = response.json()
        rows = []
        for article in payload.get("articles", []) if isinstance(payload, dict) else []:
            source = article.get("source") if isinstance(article.get("source"), dict) else {}
            rows.append(
                {
                    "title": article.get("title") or "",
                    "summary": article.get("description") or "",
                    "url": article.get("url") or "",
                    "published_at": article.get("publishedAt") or "",
                    "source": source.get("name") or "NewsAPI",
                    "credibility": "secondary",
                }
            )
        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame, error_result(source="NewsAPI", provider="newsapi", error="No NewsAPI articles returned.")
        frame["classification"] = frame.apply(lambda row: classify_geopolitical_news(row.to_dict()), axis=1)
        return dedupe_news_items(frame), ok_result(frame, source="NewsAPI", provider="newsapi", coverage=f"{len(frame)} articles")
    except Exception as exc:
        return pd.DataFrame(), error_result(source="NewsAPI", provider="newsapi", error=f"NewsAPI request failed: {exc.__class__.__name__}")


def classify_geopolitical_news(item: dict) -> str:
    text = f"{item.get('title', '')} {item.get('description', '')} {item.get('summary', '')}".lower()
    for label, keywords in CLASSIFICATION_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            return label
    return "unknown"


def _tag_from_keywords(text: str, mapping: dict[str, list[str]]) -> list[str]:
    lowered = text.lower()
    tags = [label for label, keywords in mapping.items() if any(keyword.lower() in lowered for keyword in keywords)]
    return tags or ["unclassified"]


def _freshness_label(value: object) -> str:
    try:
        published = _parse_datetime(value)
        if pd.isna(published):
            return "unknown"
        age_hours = (datetime.now(timezone.utc) - published.to_pydatetime()).total_seconds() / 3600
        if age_hours <= 24:
            return "fresh"
        if age_hours <= 72:
            return "watch"
        return "stale"
    except Exception:
        return "unknown"


def _severity_badge(classification: str) -> str:
    if classification in {"war_conflict", "chokepoint", "sanctions"}:
        return "high"
    if classification in {"pipeline", "tanker", "refinery", "opec_policy"}:
        return "medium"
    return "watch"


def _location_from_text(text: str) -> dict:
    for keyword, payload in LOCATION_KEYWORDS.items():
        if keyword.lower() in text.lower():
            return payload
    return {"lat": None, "lon": None, "location": None}


def enrich_news_items(items: pd.DataFrame) -> pd.DataFrame:
    if items is None or items.empty:
        return pd.DataFrame()
    frame = items.copy()
    for column in ["title", "description", "summary"]:
        if column not in frame.columns:
            frame[column] = ""
    if "classification" not in frame.columns:
        frame["classification"] = frame.apply(lambda row: classify_geopolitical_news(row.to_dict()), axis=1)
    text = frame[["title", "description", "summary"]].fillna("").agg(" ".join, axis=1)
    frame["asset_tags"] = text.apply(lambda value: ", ".join(_tag_from_keywords(value, ASSET_KEYWORDS)))
    frame["region_tags"] = text.apply(lambda value: ", ".join(_tag_from_keywords(value, REGION_KEYWORDS)))
    frame["freshness"] = frame.get("published_at", pd.Series(dtype=object)).apply(_freshness_label)
    frame["severity"] = frame["classification"].astype(str).apply(_severity_badge)
    locations = text.apply(_location_from_text)
    frame["lat"] = locations.apply(lambda item: item.get("lat"))
    frame["lon"] = locations.apply(lambda item: item.get("lon"))
    frame["location"] = locations.apply(lambda item: item.get("location"))
    frame["timeline_time"] = frame.get("published_at", "")
    frame["source_credibility"] = frame.get("credibility", "secondary")
    return frame


def dedupe_news_items(items: pd.DataFrame) -> pd.DataFrame:
    if items is None or items.empty:
        return pd.DataFrame()
    frame = items.copy()
    for col in ["title", "url"]:
        if col not in frame.columns:
            frame[col] = ""
    return frame.drop_duplicates(subset=["title", "url"], keep="first")


def compute_news_risk_score(items: pd.DataFrame) -> dict:
    if items is None or items.empty:
        return {"score": 0, "label": "No current news proxy", "source_status": "missing"}
    risk_labels = {"chokepoint", "sanctions", "war_conflict", "pipeline", "tanker", "refinery"}
    classified = items.get("classification", pd.Series(dtype=str)).astype(str)
    risk_count = int(classified.isin(risk_labels).sum())
    score = min(100, risk_count * 12 + len(items) * 2)
    label = "Elevated geopolitical news risk" if score >= 60 else "Moderate geopolitical news risk" if score >= 30 else "Watch-point"
    return {"score": score, "label": label, "risk_item_count": risk_count, "source_status": "heuristic news proxy"}


def build_geopolitical_news_dashboard(query: str | None = None) -> tuple[dict, object]:
    gdelt, gdelt_status = fetch_gdelt_news(query)
    rss, rss_status = fetch_public_rss_news()
    frames = [frame for frame in [gdelt, rss] if not frame.empty]
    statuses = [gdelt_status, rss_status]
    if get_settings().newsapi_key:
        newsapi, newsapi_status = fetch_newsapi_news(query)
        frames.append(newsapi) if not newsapi.empty else None
        statuses.append(newsapi_status)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    combined = enrich_news_items(dedupe_news_items(combined))
    risk = compute_news_risk_score(combined)
    timeline_cols = [col for col in ["timeline_time", "title", "source", "severity", "classification", "asset_tags", "region_tags"] if col in combined.columns]
    timeline = combined[timeline_cols].head(50) if timeline_cols and not combined.empty else pd.DataFrame()
    mapped = combined.dropna(subset=["lat", "lon"]) if {"lat", "lon"}.issubset(combined.columns) and not combined.empty else pd.DataFrame()
    payload = {"news": combined, "risk": risk, "timeline": timeline, "mapped_events": mapped, "source_status": statuses}
    if combined.empty:
        return payload, error_result(source="GDELT + RSS", provider="geopolitical_news", error="No public news data returned.", warning="News APIs can be rate limited.")
    warning = "; ".join(f"{status.provider}: {status.error}" for status in statuses if not status.ok and status.error) or None
    return payload, ok_result(payload, source="GDELT + RSS", provider="geopolitical_news", warning=warning, coverage=f"{len(combined)} items")


def build_multi_source_news_feed(query: str | None = None) -> tuple[dict, object]:
    return build_geopolitical_news_dashboard(query)


def _credibility_from_url(url: str) -> str:
    lowered = url.lower()
    if "eia.gov" in lowered or "iea.org" in lowered or "opec.org" in lowered:
        return "official"
    return "secondary"
