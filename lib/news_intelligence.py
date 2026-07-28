from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable
from urllib.parse import urlparse

from .source_freshness import source_freshness_table

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


CHANNEL_KEYWORDS = {
    "equity": ["stock", "equity", "shares", "earnings", "index", "nasdaq", "s&p", "dow"],
    "rates": ["rates", "treasury", "yield", "bond", "fed", "central bank"],
    "FX": ["dollar", "currency", "fx", "yen", "euro", "yuan", "dxy"],
    "crypto": ["bitcoin", "ether", "crypto", "stablecoin", "exchange", "token", "defi"],
    "oil": ["oil", "crude", "brent", "wti", "opec", "refinery", "cushing"],
    "shipping": ["shipping", "tanker", "canal", "strait", "vessel", "port", "freight"],
    "geopolitical": ["war", "conflict", "sanction", "missile", "attack", "border", "military"],
    "macro": ["inflation", "growth", "gdp", "jobs", "trade", "tariff", "policy"],
}

REGION_KEYWORDS = {
    "Middle East": ["hormuz", "iran", "iraq", "saudi", "israel", "gaza", "persian gulf", "opec"],
    "Red Sea": ["red sea", "bab el-mandeb", "yemen", "houthi", "suez"],
    "Europe": ["europe", "eu", "germany", "france", "uk", "north sea"],
    "Russia / Ukraine": ["russia", "ukraine", "moscow", "kyiv", "black sea"],
    "Asia": ["china", "japan", "korea", "taiwan", "singapore", "malacca", "india"],
    "Americas": ["united states", "u.s.", "us ", "canada", "mexico", "panama", "venezuela", "brazil"],
}

LOCATION_KEYWORDS = {
    "hormuz": {"lat": 26.5667, "lon": 56.25, "location": "Strait of Hormuz"},
    "suez": {"lat": 30.5852, "lon": 32.2654, "location": "Suez Canal"},
    "bab el-mandeb": {"lat": 12.5833, "lon": 43.3333, "location": "Bab el-Mandeb"},
    "red sea": {"lat": 18.0, "lon": 39.0, "location": "Red Sea"},
    "malacca": {"lat": 2.5, "lon": 101.0, "location": "Strait of Malacca"},
    "panama": {"lat": 9.08, "lon": -79.68, "location": "Panama Canal"},
    "bosphorus": {"lat": 41.12, "lon": 29.07, "location": "Bosphorus"},
    "dardanelles": {"lat": 40.15, "lon": 26.4, "location": "Dardanelles"},
    "gibraltar": {"lat": 35.96, "lon": -5.55, "location": "Strait of Gibraltar"},
    "taiwan": {"lat": 23.7, "lon": 121.0, "location": "Taiwan"},
    "ukraine": {"lat": 49.0, "lon": 32.0, "location": "Ukraine"},
}

REGION_CENTROIDS = {
    "Middle East": {"lat": 29.3, "lon": 47.7, "location": "Middle East centroid"},
    "Red Sea": {"lat": 18.0, "lon": 39.0, "location": "Red Sea centroid"},
    "Europe": {"lat": 50.1, "lon": 10.4, "location": "Europe centroid"},
    "Russia / Ukraine": {"lat": 49.0, "lon": 32.0, "location": "Russia / Ukraine centroid"},
    "Asia": {"lat": 35.9, "lon": 104.2, "location": "Asia centroid"},
    "Americas": {"lat": 39.8, "lon": -98.6, "location": "Americas centroid"},
    "Global": {"lat": 20.0, "lon": 0.0, "location": "Global centroid"},
}

RELATED_ASSETS = {
    "BTC": ["bitcoin", "btc"],
    "ETH": ["ether", "ethereum", "eth"],
    "WTI": ["wti", "crude", "oil"],
    "Brent": ["brent"],
    "DXY": ["dollar", "dxy"],
    "US10Y": ["treasury", "yield", "rates"],
    "SPX": ["s&p", "spx", "stocks", "equity"],
    "NDX": ["nasdaq", "technology"],
    "Gold": ["gold"],
}


def _frame(items: Any):
    if pd is None:
        return items or []
    if items is None:
        return pd.DataFrame()
    if isinstance(items, dict) and "news" in items:
        items = items.get("news")
    if hasattr(items, "copy") and hasattr(items, "columns"):
        return items.copy()
    if isinstance(items, list):
        return pd.DataFrame(items)
    if isinstance(items, dict):
        return pd.DataFrame([items])
    return pd.DataFrame()


def _records(items: Any) -> list[dict[str, Any]]:
    frame = _frame(items)
    if hasattr(frame, "to_dict"):
        return frame.to_dict(orient="records")
    if isinstance(frame, list):
        return [dict(item) for item in frame if isinstance(item, dict)]
    return []


def _text(item: dict[str, Any]) -> str:
    return " ".join(str(item.get(key, "") or "") for key in ["title", "summary", "description", "classification", "source"]).strip()


def _list_from(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def classify_news_asset_tags(item: dict[str, Any] | str) -> list[str]:
    text = item if isinstance(item, str) else _text(item)
    lowered = text.lower()
    tags = [channel for channel, keywords in CHANNEL_KEYWORDS.items() if any(keyword in lowered for keyword in keywords)]
    return tags or ["macro"]


def classify_news_region(item: dict[str, Any] | str) -> str:
    text = item if isinstance(item, str) else _text(item)
    lowered = text.lower()
    for region, keywords in REGION_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return region
    return "Global"


def classify_news_severity(item: dict[str, Any] | str) -> str:
    text = item if isinstance(item, str) else _text(item)
    lowered = text.lower()
    critical = ["nuclear alert", "invasion", "canal closed", "strait closed"]
    high = ["missile", "attack", "war", "conflict", "sanction", "blockade", "chokepoint", "tanker", "cyberattack", "explosion"]
    medium = ["tariff", "inflation", "rate decision", "production cut", "outage", "regulation", "default", "strike"]
    if any(keyword in lowered for keyword in critical):
        return "critical"
    if any(keyword in lowered for keyword in high):
        return "high"
    if any(keyword in lowered for keyword in medium):
        return "medium"
    return "watch"


def classify_news_credibility(item: dict[str, Any] | str) -> str:
    source = item if isinstance(item, str) else str(item.get("source") or item.get("url") or "")
    lowered = source.lower()
    if any(token in lowered for token in [".gov", "eia.gov", "iea.org", "opec.org", "federalreserve.gov", "sec.gov"]):
        return "official"
    if any(token in lowered for token in ["reuters", "bloomberg", "apnews", "ft.com", "wsj.com", "cnbc"]):
        return "major wire/media"
    if source:
        return "secondary"
    return "unknown"


def _confidence_from_credibility(credibility: str) -> float:
    return {"official": 0.88, "major wire/media": 0.72, "secondary": 0.58, "unknown": 0.35}.get(str(credibility or "unknown").lower(), 0.5)


def extract_related_assets(item: dict[str, Any] | str) -> list[str]:
    text = item if isinstance(item, str) else _text(item)
    lowered = text.lower()
    assets = [asset for asset, keywords in RELATED_ASSETS.items() if any(keyword in lowered for keyword in keywords)]
    return assets or []


def _severity_score(severity: str) -> int:
    return {"critical": 95, "high": 78, "medium": 55, "watch": 30, "low": 15}.get((severity or "").lower(), 30)


def _parse_datetime(value: Any):
    try:
        parsed = parsedate_to_datetime(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return pd.Timestamp(parsed).tz_convert("UTC")
    except Exception:
        return pd.to_datetime(value, utc=True, errors="coerce")


def _freshness(published_at: Any) -> str:
    if pd is None or published_at is None:
        return "unknown"
    timestamp = _parse_datetime(published_at)
    if pd.isna(timestamp):
        return "unknown"
    age_hours = (datetime.now(timezone.utc) - timestamp.to_pydatetime()).total_seconds() / 3600.0
    if age_hours <= 24:
        return "fresh"
    if age_hours <= 72:
        return "stale"
    return "stale"


def _location(text: str) -> dict[str, Any]:
    lowered = text.lower()
    for keyword, payload in LOCATION_KEYWORDS.items():
        if keyword in lowered:
            return {**payload, "coordinate_method": "named_location"}
    return {"lat": None, "lon": None, "location": None, "coordinate_method": "unmapped"}


def _region_location(region: str) -> dict[str, Any]:
    return {**REGION_CENTROIDS.get(region, REGION_CENTROIDS["Global"]), "coordinate_method": "region_centroid"}


def _coordinate_present(value: Any) -> bool:
    if value is None:
        return False
    if pd is not None:
        try:
            return not bool(pd.isna(value))
        except Exception:
            return True
    return True


def normalize_news_item(item: dict[str, Any]) -> dict[str, Any]:
    text = _text(item)
    severity = str(item.get("severity") or classify_news_severity(item)).lower()
    asset_tags = _list_from(item.get("asset_tags")) or classify_news_asset_tags(item)
    impact_channels = _list_from(item.get("impact_channels")) or classify_news_asset_tags(item)
    region = str(item.get("region") or classify_news_region(item))
    region_tags = _list_from(item.get("region_tags")) or [region]
    location = _location(text)
    if _coordinate_present(item.get("lat")) and _coordinate_present(item.get("lon")):
        location = {
            "lat": item.get("lat"),
            "lon": item.get("lon"),
            "location": item.get("location") or location.get("location"),
            "coordinate_method": item.get("coordinate_method") or "source_coordinates",
        }
    elif location.get("lat") is None or location.get("lon") is None:
        location = _region_location(region)
    url = item.get("url") or item.get("link") or ""
    source = item.get("source") or (urlparse(url).netloc if url else "")
    published_at = item.get("published_at") or item.get("date") or item.get("timeline_time")
    summary = item.get("summary") or item.get("description") or text[:260]
    credibility = item.get("credibility") or item.get("source_credibility") or classify_news_credibility({"source": source, "url": url})
    source_status = item.get("source_status") or item.get("freshness") or _freshness(published_at)
    return {
        "title": str(item.get("title") or "Untitled news item"),
        "summary": str(summary or "")[:320],
        "url": url,
        "source": source,
        "source_url": item.get("source_url") or url or source,
        "provider": item.get("provider") or "public_feed",
        "fetched_at": item.get("fetched_at") or item.get("checked_at") or published_at or datetime.now(timezone.utc).isoformat(),
        "published_at": published_at,
        "asset_tags": asset_tags,
        "impact_channels": impact_channels,
        "region": region,
        "region_tags": region_tags,
        "severity": severity,
        "severity_score": _severity_score(severity),
        "credibility": credibility,
        "freshness": item.get("freshness") or _freshness(published_at),
        "source_status": source_status,
        "confidence": item.get("confidence") or _confidence_from_credibility(str(credibility)),
        "related_assets": extract_related_assets(item),
        "classification_method": "heuristic",
        "lat": location.get("lat"),
        "lon": location.get("lon"),
        "location": location.get("location"),
        "coordinate_method": location.get("coordinate_method"),
        "data_gap": item.get("data_gap") or "",
        "caveat": item.get("caveat") or "Public news rows may be delayed, duplicated, or missing precise coordinates.",
    }


def _normalized_frame(items: Any):
    rows = [normalize_news_item(row) for row in _records(items)]
    if pd is None:
        return rows
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["published_at_dt"] = frame["published_at"].apply(_parse_datetime)
    return frame


def build_news_timeline(items: Any, freq: str = "D"):
    frame = _normalized_frame(items)
    if pd is None:
        return []
    columns = ["period", "total_count", "critical_count", "high_count", "medium_count", "watch_count"]
    if frame.empty or "published_at_dt" not in frame.columns:
        return pd.DataFrame(columns=columns)
    dated = frame.dropna(subset=["published_at_dt"]).copy()
    if dated.empty:
        return pd.DataFrame(columns=columns)
    dated["period"] = dated["published_at_dt"].dt.floor("h" if freq.upper().startswith("H") else "D")
    grouped = dated.groupby("period")
    rows = []
    for period, group in grouped:
        severities = group["severity"].astype(str).str.lower()
        rows.append(
            {
                "period": period,
                "total_count": int(len(group)),
                "critical_count": int((severities == "critical").sum()),
                "high_count": int((severities == "high").sum()),
                "medium_count": int((severities == "medium").sum()),
                "watch_count": int((severities == "watch").sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("period")


def build_market_impact_matrix(items: Any):
    frame = _normalized_frame(items)
    if pd is None:
        return []
    columns = ["impact_channel", "total_count", "critical_count", "high_count", "medium_count", "watch_count", "top_related_assets", "latest_title"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for channel in CHANNEL_KEYWORDS:
        subset = frame[frame["impact_channels"].apply(lambda values: channel in _list_from(values))]
        if subset.empty:
            continue
        severities = subset["severity"].astype(str).str.lower()
        assets = sorted({asset for values in subset["related_assets"] for asset in _list_from(values)})
        latest = subset.sort_values("published_at_dt", ascending=False, na_position="last").iloc[0]
        rows.append(
            {
                "impact_channel": channel,
                "total_count": int(len(subset)),
                "critical_count": int((severities == "critical").sum()),
                "high_count": int((severities == "high").sum()),
                "medium_count": int((severities == "medium").sum()),
                "watch_count": int((severities == "watch").sum()),
                "top_related_assets": ", ".join(assets[:6]),
                "latest_title": latest.get("title"),
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values(["critical_count", "high_count", "total_count"], ascending=False)


def build_high_severity_feed(items: Any, limit: int = 12):
    frame = _normalized_frame(items)
    if pd is None:
        return []
    if frame.empty:
        return frame
    severities = ["critical", "high", "medium"]
    high = frame[frame["severity"].astype(str).str.lower().isin(severities)].copy()
    if high.empty:
        high = frame.copy()
    return high.sort_values(["severity_score", "published_at_dt"], ascending=[False, False], na_position="last").head(limit)


def build_regional_news_cards(items: Any):
    frame = _normalized_frame(items)
    if pd is None:
        return []
    columns = ["region", "score", "severity", "headline_count", "high_count", "impact_channels", "latest_title", "method"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for region, group in frame.groupby("region"):
        high_count = int(group["severity"].astype(str).str.lower().isin(["critical", "high"]).sum())
        score = min(100, int(group["severity_score"].mean() + high_count * 8))
        latest = group.sort_values("published_at_dt", ascending=False, na_position="last").iloc[0]
        channels = sorted({channel for values in group["impact_channels"] for channel in _list_from(values)})
        rows.append(
            {
                "region": region,
                "score": score,
                "severity": "high" if score >= 75 else "medium" if score >= 55 else "watch",
                "headline_count": int(len(group)),
                "high_count": high_count,
                "impact_channels": ", ".join(channels),
                "latest_title": latest.get("title"),
                "method": "heuristic regional news proxy",
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values("score", ascending=False)


def build_source_freshness_panel(items: Any = None, statuses: Iterable[Any] | None = None):
    if pd is None:
        return []
    status_table = source_freshness_table(statuses or [])
    frame = _normalized_frame(items)
    rows = []
    if status_table is not None and not getattr(status_table, "empty", True):
        for row in status_table.to_dict(orient="records"):
            rows.append({**row, "feed_count": None, "error_count": 1 if row.get("error") else 0})
    if frame is not None and not frame.empty:
        for source, group in frame.groupby("source"):
            latest = group["published_at_dt"].dropna().max() if "published_at_dt" in group.columns else None
            freshness = _freshness(latest)
            rows.append(
                {
                    "provider": "public feed",
                    "source": source or "unknown",
                    "status": freshness,
                    "age_minutes": None,
                    "coverage": f"{len(group)} items",
                    "estimated": False,
                    "cached": False,
                    "paid_required": False,
                    "warning": None,
                    "error": None,
                    "feed_count": int(len(group)),
                    "error_count": 0,
                }
            )
    return pd.DataFrame(rows).drop_duplicates(subset=["provider", "source"], keep="last") if rows else pd.DataFrame(
        columns=["provider", "source", "status", "age_minutes", "coverage", "estimated", "cached", "paid_required", "warning", "error", "feed_count", "error_count"]
    )


def build_worldmonitor_style_news_dashboard(items: Any = None, statuses: Iterable[Any] | None = None) -> dict[str, Any]:
    frame = _normalized_frame(items)
    if pd is None:
        return {
            "normalized_news": frame,
            "high_severity_feed": [],
            "timeline": [],
            "impact_matrix": [],
            "regional_cards": [],
            "source_freshness": [],
            "event_rows": [],
            "risk_catalysts": [],
            "notes": ["pandas unavailable"],
        }
    high = build_high_severity_feed(frame)
    timeline = build_news_timeline(frame)
    impact = build_market_impact_matrix(frame)
    regional = build_regional_news_cards(frame)
    freshness = build_source_freshness_panel(frame, statuses)
    event_rows = frame.dropna(subset=["lat", "lon"]) if not frame.empty and {"lat", "lon"}.issubset(frame.columns) else pd.DataFrame()
    catalysts = high["title"].head(8).tolist() if hasattr(high, "empty") and not high.empty else []
    status_records = freshness.to_dict(orient="records") if hasattr(freshness, "to_dict") else []
    error_count = sum(1 for row in status_records if str(row.get("status")).lower() in {"missing", "error"})
    source_summary = {
        "status": "available" if not frame.empty else "unavailable",
        "row_count": int(len(frame)),
        "source_count": int(frame["source"].nunique()) if not frame.empty and "source" in frame.columns else 0,
        "error_count": int(error_count),
        "caveat": "No public feed rows are available; inspect source_freshness for errors." if frame.empty else "Rows are source-labeled public feed records.",
    }
    return {
        "normalized_news": frame,
        "high_severity_feed": high,
        "timeline": timeline,
        "impact_matrix": impact,
        "regional_cards": regional,
        "source_freshness": freshness,
        "source_status_summary": source_summary,
        "event_rows": event_rows,
        "risk_catalysts": catalysts,
        "notes": [
            source_summary["caveat"],
            "Classification is deterministic and heuristic.",
            "WorldMonitor is used as a workflow reference only; no runtime code is imported from it.",
            "Live AIS unavailable without a real provider; pro-gated route intelligence is optional.",
        ],
    }
