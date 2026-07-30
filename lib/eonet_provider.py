from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode


EONET_EVENTS_GEOJSON_URL = "https://eonet.gsfc.nasa.gov/api/v3/events/geojson"
MAX_EONET_ROWS = 200

CATEGORY_LAYER_MAP = {
    "drought": "droughts",
    "dusthaze": "dust_haze",
    "earthquakes": "earthquakes",
    "floods": "floods",
    "landslides": "landslides",
    "sealakeice": "sea_lake_ice",
    "severestorms": "storms_weather_alerts",
    "snow": "snow_cover",
    "tempextremes": "temperature_extremes",
    "volcanoes": "volcanoes",
    "watercolor": "water_quality_events",
    "wildfires": "fires",
}


def build_eonet_events_url(*, days: int = 30, status: str = "open") -> str:
    bounded_days = min(max(int(days), 1), 365)
    normalized_status = status if status in {"open", "closed", "all"} else "open"
    return f"{EONET_EVENTS_GEOJSON_URL}?{urlencode({'status': normalized_status, 'days': bounded_days})}"


def _parse_time(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _iso_time(value: Any, fallback: str) -> str:
    parsed = _parse_time(value)
    return parsed.isoformat() if parsed else fallback


def _safe_coordinates(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        lon = float(value[0])
        lat = float(value[1])
    except (TypeError, ValueError):
        return None
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    return lon, lat


def _feature_position(properties: dict[str, Any], geometry: dict[str, Any]) -> tuple[float, float, str, str, str] | None:
    geometry_type = str(geometry.get("type") or "")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point":
        point = _safe_coordinates(coordinates)
        if not point:
            return None
        lon, lat = point
        observed_at = str(properties.get("date") or "")
        return lon, lat, "nasa_eonet_geojson_point", observed_at, ""

    if geometry_type == "LineString" and isinstance(coordinates, list):
        valid_points = [(index, _safe_coordinates(value)) for index, value in enumerate(coordinates)]
        valid_points = [(index, point) for index, point in valid_points if point]
        if not valid_points:
            return None
        geometry_dates = properties.get("geometryDates")
        selected_index, selected_point = valid_points[-1]
        observed_at = ""
        if isinstance(geometry_dates, list):
            dated = [
                (parsed, index, point)
                for index, point in valid_points
                if index < len(geometry_dates)
                for parsed in [_parse_time(geometry_dates[index])]
                if parsed is not None
            ]
            if dated:
                parsed, selected_index, selected_point = max(dated, key=lambda item: item[0])
                observed_at = parsed.isoformat()
        if not observed_at and isinstance(geometry_dates, list) and selected_index < len(geometry_dates):
            observed_at = str(geometry_dates[selected_index] or "")
        lon, lat = selected_point
        gap = "Latest point on the EONET event track is displayed; the marker is not an area footprint."
        return lon, lat, "nasa_eonet_track_latest_point", observed_at, gap
    return None


def _category_rows(properties: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    categories = properties.get("categories")
    categories = categories if isinstance(categories, list) else []
    category_ids = [str(row.get("id") or "").strip() for row in categories if isinstance(row, dict)]
    category_ids = [value for value in category_ids if value]
    category_titles = [str(row.get("title") or "").strip() for row in categories if isinstance(row, dict)]
    category_titles = [value for value in category_titles if value]
    layer_ids = [CATEGORY_LAYER_MAP.get(value.lower(), "natural_events") for value in category_ids]
    return list(dict.fromkeys(category_ids)), list(dict.fromkeys(category_titles)), list(dict.fromkeys(layer_ids or ["natural_events"]))


def _severity(category_ids: list[str], magnitude: Any) -> str:
    categories = {value.lower() for value in category_ids}
    if categories & {"severestorms", "volcanoes"}:
        return "high"
    if "wildfires" in categories:
        try:
            value = float(magnitude)
        except (TypeError, ValueError):
            value = 0.0
        if value >= 10_000:
            return "high"
        if value >= 1_000:
            return "elevated"
    if categories & {"floods", "landslides", "tempextremes"}:
        return "elevated"
    return "watch"


def _source_rows(properties: dict[str, Any]) -> tuple[list[str], list[str]]:
    sources = properties.get("sources")
    sources = sources if isinstance(sources, list) else []
    source_ids = [str(row.get("id") or "").strip() for row in sources if isinstance(row, dict)]
    source_urls = [str(row.get("url") or "").strip() for row in sources if isinstance(row, dict)]
    return [value for value in source_ids if value], [value for value in source_urls if value.startswith(("http://", "https://"))]


def normalize_eonet_geojson(
    payload: Any,
    *,
    fetched_at: str | None = None,
    limit: int = MAX_EONET_ROWS,
) -> list[dict[str, Any]]:
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    features = payload.get("features") if isinstance(payload, dict) else []
    features = features if isinstance(features, list) else []
    latest_by_event: dict[str, tuple[datetime, dict[str, Any]]] = {}

    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            continue
        event_id = str(properties.get("id") or "").strip()
        position = _feature_position(properties, geometry)
        if not event_id or not position:
            continue
        lon, lat, coordinate_method, observed_at, coordinate_gap = position
        timestamp = _iso_time(properties.get("date") or observed_at, fetched_at)
        sort_time = _parse_time(timestamp) or datetime.min.replace(tzinfo=timezone.utc)
        category_ids, category_titles, layer_ids = _category_rows(properties)
        source_ids, source_urls = _source_rows(properties)
        eonet_url = str(properties.get("link") or f"https://eonet.gsfc.nasa.gov/api/v3/events/{event_id}")
        magnitude = properties.get("magnitudeValue")
        row = {
            "event_id": event_id,
            "title": str(properties.get("title") or "NASA EONET natural event"),
            "summary": str(properties.get("description") or "")[:500],
            "timestamp": timestamp,
            "published_at": timestamp,
            "lat": lat,
            "lon": lon,
            "domain": "natural",
            "severity": _severity(category_ids, magnitude),
            "severity_method": "category-and-reported-magnitude-context/not-impact-estimate",
            "category_ids": category_ids,
            "category_titles": category_titles,
            "layer_ids": layer_ids,
            "magnitude": magnitude,
            "magnitude_unit": properties.get("magnitudeUnit"),
            "provider": "nasa_eonet",
            "source": "NASA Earth Observatory Natural Event Tracker (EONET)",
            "source_url": source_urls[0] if source_urls else eonet_url,
            "upstream_source_urls": source_urls,
            "upstream_source_ids": source_ids,
            "eonet_url": eonet_url,
            "credibility": "official-aggregator",
            "confidence": 0.9,
            "coordinate_method": coordinate_method,
            "coordinate_status": "source-backed",
            "geometry_type": str(geometry.get("type") or "unknown"),
            "data_gap": coordinate_gap,
            "caveat": (
                "NASA EONET aggregates natural-event metadata from upstream sources; "
                "verify the EONET event and original source for revisions, scope, and reuse terms."
            ),
            "fetched_at": fetched_at,
            "not_financial_advice": True,
        }
        current = latest_by_event.get(event_id)
        if current is None or sort_time >= current[0]:
            latest_by_event[event_id] = (sort_time, row)

    bounded_limit = min(max(int(limit), 1), MAX_EONET_ROWS)
    ordered = sorted(latest_by_event.values(), key=lambda item: (item[0], item[1]["event_id"]), reverse=True)
    return [row for _, row in ordered[:bounded_limit]]
