from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


SEVERITY_ORDER = {"low": 10, "watch": 25, "elevated": 50, "high": 75, "critical": 95}
CREDIBILITY_ORDER = {"unknown": 10, "osint": 25, "secondary": 40, "wire": 65, "primary": 80, "official": 95}

REGIONAL_CENTROIDS = {
    "global": {"lat": None, "lon": None, "label": "Global"},
    "middle east": {"lat": 29.3, "lon": 47.7, "label": "Middle East"},
    "red sea": {"lat": 18.0, "lon": 39.0, "label": "Red Sea"},
    "europe": {"lat": 50.1, "lon": 10.4, "label": "Europe"},
    "russia / ukraine": {"lat": 49.0, "lon": 32.0, "label": "Russia / Ukraine"},
    "asia": {"lat": 35.9, "lon": 104.2, "label": "Asia"},
    "northeast asia": {"lat": 37.5, "lon": 127.5, "label": "Northeast Asia"},
    "korea": {"lat": 36.4, "lon": 127.8, "label": "Korea"},
    "americas": {"lat": 39.8, "lon": -98.6, "label": "Americas"},
}

COUNTRY_CENTROIDS = {
    "iran": {"lat": 32.0, "lon": 53.0, "region": "Middle East"},
    "israel": {"lat": 31.0, "lon": 35.0, "region": "Middle East"},
    "ukraine": {"lat": 49.0, "lon": 32.0, "region": "Russia / Ukraine"},
    "russia": {"lat": 56.0, "lon": 38.0, "region": "Russia / Ukraine"},
    "china": {"lat": 35.9, "lon": 104.2, "region": "Asia"},
    "taiwan": {"lat": 23.7, "lon": 121.0, "region": "Asia"},
    "south korea": {"lat": 36.4, "lon": 127.8, "region": "Korea"},
    "korea": {"lat": 36.4, "lon": 127.8, "region": "Korea"},
    "united states": {"lat": 39.8, "lon": -98.6, "region": "Americas"},
}

CHOKEPOINTS = [
    {"title": "Strait of Hormuz", "region": "Middle East", "country": "Iran / Oman", "lat": 26.5667, "lon": 56.25, "related_tickers": ["CL=F", "BZ=F", "XLE", "DXY"]},
    {"title": "Suez Canal", "region": "Red Sea", "country": "Egypt", "lat": 30.5852, "lon": 32.2654, "related_tickers": ["CL=F", "BZ=F", "BDRY"]},
    {"title": "Bab el-Mandeb", "region": "Red Sea", "country": "Yemen / Djibouti", "lat": 12.5833, "lon": 43.3333, "related_tickers": ["CL=F", "BZ=F", "BDRY"]},
    {"title": "Strait of Malacca", "region": "Asia", "country": "Malaysia / Indonesia", "lat": 2.5, "lon": 101.0, "related_tickers": ["CL=F", "BZ=F", "EWY"]},
    {"title": "Panama Canal", "region": "Americas", "country": "Panama", "lat": 9.08, "lon": -79.68, "related_tickers": ["BDRY", "DXY"]},
    {"title": "Bosphorus", "region": "Europe", "country": "Turkey", "lat": 41.12, "lon": 29.07, "related_tickers": ["CL=F", "BZ=F"]},
    {"title": "Dardanelles", "region": "Europe", "country": "Turkey", "lat": 40.15, "lon": 26.4, "related_tickers": ["CL=F", "BZ=F"]},
    {"title": "Strait of Gibraltar", "region": "Europe", "country": "Spain / Morocco", "lat": 35.96, "lon": -5.55, "related_tickers": ["BDRY", "BZ=F"]},
]


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return value.to_dict(orient="records")
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        if "news" in value:
            return _records(value.get("news"))
        return [dict(value)]
    return []


def _frame(rows: list[dict[str, Any]]):
    return pd.DataFrame(rows) if pd is not None else rows


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def _event_id(item: dict[str, Any]) -> str:
    if item.get("event_id"):
        return str(item["event_id"])
    seed = "|".join(str(item.get(key, "")) for key in ["timestamp", "title", "source", "region", "domain"])
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def _severity(value: Any) -> str:
    normalized = str(value or "watch").lower()
    if normalized == "medium":
        return "elevated"
    if normalized in SEVERITY_ORDER:
        return normalized
    return "watch"


def _confidence(value: Any, credibility: str, is_estimated: bool) -> float:
    try:
        number = float(value)
        if number > 1:
            number = number / 100.0
        return max(0.0, min(1.0, number))
    except Exception:
        base = CREDIBILITY_ORDER.get(credibility, 35) / 100.0
        return max(0.15, min(0.85, base - (0.15 if is_estimated else 0.0)))


def _infer_location(item: dict[str, Any]) -> tuple[Any, Any, bool, str | None, str | None, str]:
    lat = item.get("lat")
    lon = item.get("lon")
    if lat is not None and lon is not None:
        return lat, lon, False, None, None, str(item.get("coordinate_method") or "source_coordinates")
    country = str(item.get("country") or "").strip().lower()
    if country in COUNTRY_CENTROIDS:
        loc = COUNTRY_CENTROIDS[country]
        return loc["lat"], loc["lon"], True, loc.get("region"), "Coordinate uses approximate country centroid.", "country_centroid"
    region = str(item.get("region") or "").strip().lower()
    if region in REGIONAL_CENTROIDS and REGIONAL_CENTROIDS[region]["lat"] is not None:
        loc = REGIONAL_CENTROIDS[region]
        return loc["lat"], loc["lon"], True, loc["label"], "Coordinate uses approximate regional centroid.", "region_centroid"
    return None, None, False, None, "No coordinate or safe centroid available.", "unmapped"


def normalize_event(item: dict[str, Any]) -> dict[str, Any]:
    credibility = str(item.get("credibility") or item.get("source_credibility") or "unknown").lower()
    if credibility == "major wire/media":
        credibility = "wire"
    if credibility not in CREDIBILITY_ORDER:
        credibility = "secondary" if credibility else "unknown"
    lat, lon, approximate_location, inferred_region, location_gap, coordinate_method = _infer_location(item)
    severity = _severity(item.get("severity"))
    data_gap_items = _list(item.get("data_gap") or item.get("data_gaps"))
    if location_gap:
        data_gap_items.append(location_gap)
    is_estimated = bool(item.get("is_estimated") or approximate_location or item.get("classification_method") == "heuristic")
    region = item.get("region") or inferred_region or "Global"
    source_url = item.get("source_url") or item.get("url") or item.get("link") or ""
    fetched_at = str(item.get("fetched_at") or _now_iso())
    freshness = str(item.get("freshness_status") or item.get("freshness") or item.get("source_status") or "unknown").lower()
    event = {
        "event_id": _event_id(item),
        "timestamp": str(item.get("timestamp") or item.get("published_at") or item.get("date") or item.get("timeline_time") or _now_iso()),
        "title": str(item.get("title") or item.get("name") or "Untitled event"),
        "summary": str(item.get("summary") or item.get("description") or item.get("classification") or "")[:500],
        "domain": str(item.get("domain") or item.get("impact_channel") or item.get("channel") or "unknown").lower(),
        "severity": severity,
        "severity_score": SEVERITY_ORDER[severity],
        "confidence": _confidence(item.get("confidence"), credibility, is_estimated),
        "region": str(region),
        "country": item.get("country"),
        "lat": lat,
        "lon": lon,
        "approximate_location": approximate_location,
        "related_assets": _list(item.get("related_assets") or item.get("asset_tags")),
        "related_tickers": _list(item.get("related_tickers") or item.get("tickers")),
        "source": str(item.get("source") or "public/proxy"),
        "provider": str(item.get("provider") or item.get("source_provider") or "heuristic"),
        "credibility": credibility,
        "source_url": str(source_url),
        "fetched_at": fetched_at,
        "freshness": freshness,
        "freshness_status": freshness,
        "source_status": str(item.get("source_status") or freshness),
        "coordinate_method": coordinate_method,
        "is_estimated": is_estimated,
        "data_gap": "; ".join(dict.fromkeys(data_gap_items)),
        "caveat": str(item.get("caveat") or ""),
        "url": item.get("url") or item.get("link") or "",
    }
    if not event["related_tickers"] and event["related_assets"]:
        event["related_tickers"] = event["related_assets"]
    return event


def merge_news_events(news: Any = None) -> list[dict[str, Any]]:
    rows = []
    for item in _records(news):
        channels = _list(item.get("impact_channels") or item.get("asset_tags")) or ["news"]
        rows.append(
            normalize_event(
                {
                    **item,
                    "domain": channels[0],
                    "provider": item.get("provider") or "public news",
                    "source": item.get("source") or "public feed",
                    "is_estimated": item.get("is_estimated", True),
                }
            )
        )
    return rows


def merge_market_events(market_rows: Any = None) -> list[dict[str, Any]]:
    rows = []
    for item in _records(market_rows):
        ticker = item.get("ticker") or item.get("label") or item.get("asset")
        change = item.get("change_pct") or item.get("return_1d_pct") or item.get("period_return_pct")
        severity = "watch"
        try:
            absolute = abs(float(change))
            severity = "high" if absolute >= 4 else "elevated" if absolute >= 2 else "watch"
        except Exception:
            pass
        rows.append(
            normalize_event(
                {
                    "timestamp": item.get("timestamp") or _now_iso(),
                    "title": f"{ticker or 'Market asset'} move context",
                    "summary": "Observed related market move; correlation context only.",
                    "domain": "market",
                    "severity": severity,
                    "region": item.get("region") or "Global",
                    "related_tickers": [ticker] if ticker else [],
                    "source": item.get("source") or "market data",
                    "provider": item.get("provider") or "public market data",
                    "freshness_status": item.get("freshness_status") or item.get("data_status") or "unknown",
                    "is_estimated": False,
                    "data_gap": item.get("data_gap") or "",
                }
            )
        )
    return rows


def merge_crypto_events(crypto_rows: Any = None) -> list[dict[str, Any]]:
    rows = []
    for item in _records(crypto_rows):
        symbol = item.get("symbol") or item.get("ticker") or "crypto"
        stress = item.get("stress_score") or item.get("pressure_score") or 0
        severity = "high" if float(stress or 0) >= 75 else "elevated" if float(stress or 0) >= 50 else "watch"
        rows.append(
            normalize_event(
                {
                    "timestamp": item.get("timestamp") or _now_iso(),
                    "title": f"{symbol} derivatives stress context",
                    "summary": "Crypto derivatives proxy; verify exchange source data.",
                    "domain": "crypto",
                    "severity": severity,
                    "region": "Global",
                    "related_tickers": [symbol],
                    "source": item.get("source") or "crypto derivatives",
                    "provider": item.get("provider") or "public crypto endpoint",
                    "freshness_status": item.get("freshness_status") or "unknown",
                    "is_estimated": bool(item.get("is_estimated", True)),
                    "data_gap": item.get("data_gap") or "Stress score is a proxy, not a trade directive.",
                }
            )
        )
    return rows


def merge_energy_events(energy_rows: Any = None) -> list[dict[str, Any]]:
    rows = []
    for item in _records(energy_rows):
        rows.append(
            normalize_event(
                {
                    **item,
                    "domain": item.get("domain") or "energy",
                    "provider": item.get("provider") or "energy proxy",
                    "source": item.get("source") or "public/static energy context",
                    "is_estimated": item.get("is_estimated", True),
                }
            )
        )
    return rows


def merge_natural_events(natural_rows: Any = None) -> list[dict[str, Any]]:
    rows = []
    for item in _records(natural_rows):
        rows.append(
            normalize_event(
                {
                    **item,
                    "domain": item.get("domain") or "natural",
                    "provider": item.get("provider") or "public natural event feed",
                    "source": item.get("source") or "public natural event feed",
                    "credibility": item.get("credibility") or "official",
                    "is_estimated": item.get("is_estimated", False),
                }
            )
        )
    return rows


def merge_flight_events(flight_rows: Any = None) -> list[dict[str, Any]]:
    rows = []
    for item in _records(flight_rows):
        rows.append(
            normalize_event(
                {
                    **item,
                    "domain": "flight",
                    "provider": item.get("provider") or "opensky",
                    "source": item.get("source") or "OpenSky Network",
                    "credibility": item.get("credibility") or "official",
                    "is_estimated": item.get("is_estimated", False),
                }
            )
        )
    return rows


def merge_chokepoint_events(chokepoints: Any = None) -> list[dict[str, Any]]:
    source_rows = _records(chokepoints) or CHOKEPOINTS
    rows = []
    for item in source_rows:
        rows.append(
            normalize_event(
                {
                    **item,
                    "summary": item.get("summary") or "Static chokepoint watch-point; no live AIS or vessel flow is claimed.",
                    "domain": "chokepoints",
                    "severity": item.get("severity") or "watch",
                    "source": item.get("source") or "static chokepoint registry",
                    "source_url": item.get("source_url") or "local://static-chokepoints",
                    "provider": "local",
                    "freshness_status": "estimated",
                    "source_status": "static/proxy",
                    "coordinate_method": item.get("coordinate_method") or "static_registry",
                    "is_estimated": True,
                    "data_gap": item.get("data_gap") or "Static registry only; live vessel data unavailable.",
                    "caveat": item.get("caveat") or "Static/proxy chokepoint row; no live AIS or vessel flow is claimed.",
                }
            )
        )
    return rows


def dedupe_events(events: Any) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in [normalize_event(row) for row in _records(events)]:
        key = item.get("event_id") or f"{item.get('title')}|{item.get('timestamp')}"
        if key in seen:
            continue
        seen.add(str(key))
        output.append(item)
    return output


def rank_events_by_severity(events: Any) -> list[dict[str, Any]]:
    rows = dedupe_events(events)
    return sorted(rows, key=lambda item: (SEVERITY_ORDER.get(item.get("severity"), 0), item.get("timestamp", "")), reverse=True)


def build_event_stream(
    news: Any = None,
    market: Any = None,
    crypto: Any = None,
    energy: Any = None,
    chokepoints: Any = None,
    natural: Any = None,
    flight: Any = None,
) -> list[dict[str, Any]]:
    events = []
    events.extend(merge_news_events(news))
    events.extend(merge_market_events(market))
    events.extend(merge_crypto_events(crypto))
    events.extend(merge_energy_events(energy))
    events.extend(merge_natural_events(natural))
    events.extend(merge_flight_events(flight))
    events.extend(merge_chokepoint_events(chokepoints))
    return rank_events_by_severity(events)


def build_event_timeline(events: Any, freq: str = "D"):
    rows = dedupe_events(events)
    if pd is None:
        return rows
    columns = ["period", "event_count", "critical_count", "high_count", "elevated_count", "watch_count", "low_count"]
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows)
    frame["timestamp_dt"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    dated = frame.dropna(subset=["timestamp_dt"]).copy()
    if dated.empty:
        return pd.DataFrame(columns=columns)
    dated["period"] = dated["timestamp_dt"].dt.floor("h" if freq.upper().startswith("H") else "D")
    grouped = dated.groupby("period")
    out = []
    for period, group in grouped:
        severities = group["severity"].astype(str).str.lower()
        out.append(
            {
                "period": period,
                "event_count": int(len(group)),
                "critical_count": int((severities == "critical").sum()),
                "high_count": int((severities == "high").sum()),
                "elevated_count": int((severities == "elevated").sum()),
                "watch_count": int((severities == "watch").sum()),
                "low_count": int((severities == "low").sum()),
            }
        )
    return pd.DataFrame(out, columns=columns).sort_values("period")


def build_event_feed_cards(events: Any, limit: int = 12) -> list[dict[str, Any]]:
    cards = []
    for event in rank_events_by_severity(events)[:limit]:
        cards.append(
            {
                "title": event["title"],
                "summary": event["summary"] or "No summary supplied.",
                "severity": event["severity"],
                "freshness": event["freshness_status"],
                "source": event["source"],
                "tags": [event["domain"], event["region"]] + event.get("related_tickers", [])[:4],
                "bullets": [
                    f"Credibility: {event['credibility']}",
                    "Location is approximate." if event.get("approximate_location") else "Location from source/static registry.",
                    event.get("data_gap") or "No explicit data gap supplied.",
                ],
                "event_id": event["event_id"],
                "url": event.get("url"),
            }
        )
    return cards
