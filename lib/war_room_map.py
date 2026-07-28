from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable

from .event_asset_graph import build_event_asset_graph_contract
from .event_stream import dedupe_events
from .layer_registry import build_layer_runtime_payload
from .provider_health_engine import recommended_action_for_status


WAR_ROOM_MAP_VERSION = "war_room_map.v1"

NON_ADVISORY_CAVEAT = "Research map context only; not financial advice and not an execution or order-routing surface."
PROXY_LAYER_CAVEAT = "Proxy/static layers are context only and must not be labeled as live telemetry."
LIVE_PROVIDER_CAVEAT = "Live AIS, flight, sanctions, and vessel-tracking coverage is unavailable until a real provider is configured and probed."

SOURCE_BACKED_STATUSES = {"live/fresh", "cached", "fresh", "available", "fixture"}
LIMITED_STATUSES = {"stale", "rate-limited", "proxy/static", "static/proxy", "fixture", "inferred/proxy"}
UNAVAILABLE_STATUSES = {"missing-key", "forbidden/subscription-blocked", "unavailable", "provider-required", "missing"}


EVIDENCE_REFS = [
    {
        "external_project": "WorldMonitor",
        "evidence_ref": "Phase 2E WorldMonitor map/layer/provider-health evidence cards",
        "license_stance": "behavior-only/agpl-boundary",
        "usage": "Source-status-aware map layer controls, marker inspection, and caveat discipline.",
        "copied_source": False,
        "local_target": "lib/war_room_map.py and apps/web war-room-map view",
        "required_tests": ["tests/test_war_room_map_contracts.py"],
        "caveat": "AGPL source is not copied; this is a first-party JSON contract.",
    },
    {
        "external_project": "worldview",
        "evidence_ref": "Phase 2E worldview layer/timeline/compare evidence cards",
        "license_stance": "behavior-only/nasa-license-caution",
        "usage": "Timeline filter and compare-window contract shape only.",
        "copied_source": False,
        "local_target": "timeline_filters and compare_windows",
        "required_tests": ["tests/test_war_room_map_contracts.py"],
        "caveat": "No worldview source, assets, or NASA layer definitions are copied.",
    },
    {
        "external_project": "osiris",
        "evidence_ref": "Phase 2E osiris OSINT map evidence cards",
        "license_stance": "behavior-reference/mit-compatible",
        "usage": "Explicit provider gating for earthquakes, flight, sanctions, and news-style OSINT layers.",
        "copied_source": False,
        "local_target": "provider_requirements and readiness.unavailable_capabilities",
        "required_tests": ["tests/test_war_room_map_contracts.py"],
        "caveat": "No external source is vendored; unavailable live OSINT rows remain visible as gaps.",
    },
    {
        "external_project": "OpenBB",
        "evidence_ref": "Phase 2E OpenBB provider-contract evidence cards",
        "license_stance": "behavior-only/agpl-boundary",
        "usage": "Provider hierarchy and status-gated data contract behavior.",
        "copied_source": False,
        "local_target": "provider_requirements",
        "required_tests": ["tests/test_war_room_map_contracts.py"],
        "caveat": "OpenBB remains optional and is not added as a dependency.",
    },
    {
        "external_project": "BB-Terminal / Bloomberg-style references",
        "evidence_ref": "Phase 2E/3 terminal-workstation evidence cards",
        "license_stance": "behavior-only/direct-copy-blocked",
        "usage": "Dense workstation layout and source/caveat rail behavior.",
        "copied_source": False,
        "local_target": "apps/web war-room-map view",
        "required_tests": ["npm --prefix apps/web run build"],
        "caveat": "No terminal source, data routes, or visual assets are copied.",
    },
    {
        "external_project": "Phase 2F Event-To-Asset Graph",
        "evidence_ref": "docs/PHASE_2F_EVENT_ASSET_GRAPH_SPEC.md",
        "license_stance": "first-party",
        "usage": "Related graph node IDs and command/map context for markers.",
        "copied_source": False,
        "local_target": "markers.related_asset_node_ids",
        "required_tests": ["tests/test_war_room_map_contracts.py"],
        "caveat": "Graph persistence remains unavailable.",
    },
]


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return [dict(item) for item in value.to_dict(orient="records")]
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ["data", "events", "layers", "ledger", "nodes", "source_status"]:
            if isinstance(value.get(key), list):
                return _records(value.get(key))
        return [dict(value)]
    return []


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _marker_id(row: dict[str, Any]) -> str:
    if row.get("event_id"):
        return f"marker:{row['event_id']}"
    seed = "|".join(str(row.get(key, "")) for key in ["timestamp", "title", "source", "region", "domain"])
    return f"marker:{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:16]}"


def _normalize_status(value: Any, fallback: str = "unavailable") -> str:
    status = str(value or fallback).strip().lower().replace("_", "-")
    if status in {"fresh", "available", "ok", "configured", "live"}:
        return "live/fresh"
    if status in {"static", "static/proxy"}:
        return "proxy/static"
    if status in {"missing", "missing-key"}:
        return "missing-key"
    if "forbidden" in status or "unauthorized" in status or "subscription" in status:
        return "forbidden/subscription-blocked"
    if "rate" in status and "limit" in status:
        return "rate-limited"
    if "proxy" in status or "static" in status:
        return "proxy/static"
    if status in SOURCE_BACKED_STATUSES | LIMITED_STATUSES | UNAVAILABLE_STATUSES:
        return status
    return fallback


def _availability_for_status(status: str) -> str:
    normalized = _normalize_status(status)
    if normalized in {"live/fresh", "cached"}:
        return "available"
    if normalized in LIMITED_STATUSES:
        return "limited"
    return "unavailable"


def _confidence(value: Any, fallback: float = 0.45) -> float:
    try:
        number = float(value)
        if number > 1:
            number = number / 100.0
        return round(max(0.05, min(0.99, number)), 2)
    except Exception:
        return fallback


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        number = float(value)
        if number != number:
            return None
        return number
    except Exception:
        return None


def _coordinate_quality(row: dict[str, Any]) -> tuple[str, str]:
    method = str(row.get("coordinate_method") or "unmapped").strip().lower()
    status = str(row.get("coordinate_status") or "").strip().lower()
    if status:
        return method, status
    if _float_or_none(row.get("lat")) is None or _float_or_none(row.get("lon")) is None:
        return method, "unavailable"
    if method in {
        "source_coordinates",
        "provider_coordinates",
        "reported_coordinates",
        "usgs_geojson",
        "opensky_state_vector",
        "nws_geometry",
        "nasa_firms_coordinates",
    } and not row.get("approximate_location"):
        return method, "source-backed"
    if "fixture" in method:
        return method, "fixture"
    if method in {"static_registry", "static_coordinates"} or "static" in method:
        return method, "static/proxy"
    if method in {"region_centroid", "country_centroid", "named_location"} or row.get("approximate_location"):
        return method, "approximate"
    return method, "approximate"


def _coordinate_caveat(status: str, method: str) -> str:
    if status == "source-backed":
        return "Coordinates come from the source/provider row."
    if status == "fixture":
        return "Coordinates are fixture coordinates for deterministic UI development."
    if status == "static/proxy":
        return "Coordinates come from a static/proxy registry, not live telemetry."
    if status == "approximate":
        return f"Coordinates are approximate via {method}; inspect source before use."
    return "Marker is unavailable on the map because coordinates are missing."


def _broad_region(lat: float, lon: float) -> str:
    if lat <= -55:
        return "Antarctic"
    if -50 <= lat <= 5 and 110 <= lon <= 180:
        return "Oceania"
    if 5 < lat <= 45 and 25 <= lon <= 65:
        return "Middle East"
    if -40 <= lat <= 38 and -20 <= lon <= 55:
        return "Africa"
    if 35 <= lat <= 72 and -25 <= lon <= 45:
        return "Europe"
    if -60 <= lat <= 75 and -170 <= lon <= -30:
        return "Americas"
    if -15 <= lat <= 75 and 45 < lon <= 180:
        return "Asia"
    if lon >= 110 or lon <= -110:
        return "Pacific"
    return "Global"


def _region_with_method(row: dict[str, Any], lat: float, lon: float) -> tuple[str, str]:
    region = str(row.get("region") or "").strip()
    if region and region.lower() not in {"global", "unknown", "none"}:
        return region, "provider-reported"
    derived = _broad_region(lat, lon)
    if derived != "Global":
        return derived, "coordinate-derived-broad-region"
    return "Global", "provider-default"


def _severity_score(value: Any) -> int:
    severity = str(value or "watch").lower()
    return {"critical": 95, "high": 78, "elevated": 55, "medium": 55, "watch": 30, "low": 15}.get(severity, 30)


def _parse_time(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _event_node_lookup(event_graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for node in _records(event_graph.get("nodes") if isinstance(event_graph, dict) else []):
        if node.get("type") != "event":
            continue
        metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        event_id = str(metadata.get("event_id") or "").strip()
        if event_id:
            lookup[event_id] = node
    return lookup


def _related_asset_node_ids(marker_event_node_id: str | None, event_graph: dict[str, Any]) -> list[str]:
    if not marker_event_node_id:
        return []
    node_types = {
        str(node.get("id")): str(node.get("type"))
        for node in _records(event_graph.get("nodes") if isinstance(event_graph, dict) else [])
    }
    asset_types = {"asset_class", "commodity", "fx_pair", "crypto_pair", "sector", "index", "risk_theme"}
    related = []
    for edge in _records(event_graph.get("edges") if isinstance(event_graph, dict) else []):
        if edge.get("source") == marker_event_node_id and node_types.get(str(edge.get("target"))) in asset_types:
            related.append(str(edge.get("target")))
    return sorted(dict.fromkeys(related))


def _layer_ids_for_event(row: dict[str, Any], layers: list[dict[str, Any]]) -> list[str]:
    domain = str(row.get("domain") or "").lower()
    text = " ".join(str(row.get(key) or "") for key in ["title", "summary", "source", "region"]).lower()
    layer_ids: set[str] = set()
    if domain in {"chokepoints", "shipping", "energy"} or any(token in text for token in ["hormuz", "suez", "red sea", "bab el-mandeb", "vessel", "tanker"]):
        layer_ids.add("chokepoints")
    if domain == "natural" or any(token in text for token in ["earthquake", "usgs", "storm", "wildfire"]):
        layer_ids.add("earthquakes")
    if domain == "flight" or any(token in text for token in ["opensky", "aircraft state", "flight tracking"]):
        layer_ids.add("flight_tracking_unavailable")
    if domain == "crypto" or any(token in text for token in ["crypto", "bitcoin", "binance", "coingecko"]):
        layer_ids.add("crypto")
        layer_ids.add("oi_funding_stress")
    if domain in {"market", "equity", "rates", "fx"} or any(token in text for token in ["fed", "rates", "treasury", "dxy", "stock", "equity"]):
        layer_ids.add("major_indices")
    if domain in {"geopolitical", "oil", "shipping"} or any(token in text for token in ["attack", "war", "conflict", "sanction", "policy", "missile"]):
        layer_ids.add("conflicts")
    if not layer_ids:
        layer_ids.add("conflicts")
    existing = {str(layer.get("layer_id")) for layer in layers}
    return sorted(layer_id for layer_id in layer_ids if layer_id in existing)


def _build_marker(row: dict[str, Any], layers: list[dict[str, Any]], event_graph: dict[str, Any]) -> dict[str, Any] | None:
    lat = _float_or_none(row.get("lat"))
    lon = _float_or_none(row.get("lon"))
    method, coordinate_status = _coordinate_quality(row)
    if lat is None or lon is None:
        return None
    event_id = str(row.get("event_id") or "").strip()
    event_node = _event_node_lookup(event_graph).get(event_id, {})
    event_node_id = str(event_node.get("id") or "") or None
    source_status = _normalize_status(row.get("source_status") or row.get("freshness_status") or row.get("freshness"), "proxy/static")
    source_url = str(row.get("source_url") or row.get("url") or row.get("link") or "")
    provider = str(row.get("provider") or "unknown")
    fetched_at = str(row.get("fetched_at") or row.get("timestamp") or _now_iso())
    data_gap = str(row.get("data_gap") or "")
    coordinate_note = _coordinate_caveat(coordinate_status, method)
    region, region_method = _region_with_method(row, lat, lon)
    if coordinate_status != "source-backed" and coordinate_note not in data_gap:
        data_gap = "; ".join(part for part in [data_gap, coordinate_note] if part)
    layer_ids = _layer_ids_for_event(row, layers)
    return {
        "marker_id": _marker_id(row),
        "event_id": event_id,
        "title": str(row.get("title") or "Untitled map event"),
        "summary": str(row.get("summary") or "")[:500],
        "lat": lat,
        "lon": lon,
        "coordinate_method": method,
        "coordinate_status": coordinate_status,
        "source_status": source_status,
        "availability": _availability_for_status(source_status),
        "provider": provider,
        "source": str(row.get("source") or provider),
        "source_url": source_url or "proxy/static",
        "fetched_at": fetched_at,
        "freshness": str(row.get("freshness") or row.get("freshness_status") or source_status),
        "confidence": _confidence(row.get("confidence")),
        "severity": str(row.get("severity") or "watch").lower(),
        "severity_score": _severity_score(row.get("severity")),
        "region": region,
        "region_method": region_method,
        "domain": str(row.get("domain") or "unknown").lower(),
        "layer_ids": layer_ids,
        "related_asset_node_ids": _related_asset_node_ids(event_node_id, event_graph),
        "event_graph_node_id": event_node_id,
        "timestamp": str(row.get("timestamp") or fetched_at),
        "caveat": str(row.get("caveat") or "Source, confidence, and coordinate caveats must be reviewed before use."),
        "data_gap": data_gap,
        "not_financial_advice": True,
    }


def _build_layer(row: dict[str, Any]) -> dict[str, Any]:
    status = _normalize_status(row.get("source_status") or row.get("freshness_status") or row.get("status"))
    return {
        "layer_id": str(row.get("layer_id") or "unknown"),
        "label": str(row.get("label") or row.get("layer_id") or "Unknown layer"),
        "domain": str(row.get("domain") or "unknown"),
        "provider": str(row.get("provider") or "none"),
        "source": str(row.get("source") or row.get("provider") or ""),
        "source_status": status,
        "availability": str(row.get("availability") or _availability_for_status(status)),
        "row_count": int(row.get("row_count") or 0),
        "requires_key": row.get("requires_key"),
        "freshness": status,
        "latest_fetched_at": row.get("latest_fetched_at"),
        "caveat": str(row.get("caveat") or PROXY_LAYER_CAVEAT),
        "data_gap": _layer_data_gap(row, status),
        "recommended_action": str(row.get("recommended_action") or recommended_action_for_status(status)),
    }


def _layer_data_gap(row: dict[str, Any], status: str) -> str:
    if str(row.get("layer_id")) in {"ais_unavailable", "flight_tracking_unavailable", "sanctions"}:
        return LIVE_PROVIDER_CAVEAT
    if status in UNAVAILABLE_STATUSES:
        return "Provider evidence is missing or unavailable; keep the layer disabled."
    if status == "proxy/static":
        return PROXY_LAYER_CAVEAT
    if int(row.get("row_count") or 0) == 0 and status in {"live/fresh", "cached"}:
        return "Provider is available but returned no current rows for this layer."
    return "No additional layer data gap reported."


def _timeline_filters(markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timestamps = [_parse_time(marker.get("timestamp")) for marker in markers]
    timestamps = [item for item in timestamps if item is not None]
    reference_time = max(timestamps) if timestamps else datetime.now(timezone.utc)
    windows = [
        ("6h", "Last 6h", 6),
        ("24h", "Last 24h", 24),
        ("7d", "Last 7d", 24 * 7),
        ("30d", "Last 30d", 24 * 30),
        ("all", "All fixture/runtime rows", None),
    ]
    rows = []
    for window_id, label, hours in windows:
        if hours is None:
            count = len(markers)
        else:
            count = 0
            for marker, timestamp in zip(markers, [_parse_time(marker.get("timestamp")) for marker in markers]):
                if timestamp and (reference_time - timestamp).total_seconds() <= hours * 3600:
                    count += 1
        rows.append(
            {
                "filter_id": window_id,
                "label": label,
                "window_hours": hours,
                "marker_count": count,
                "available": True,
                "source_status": "schema-ready/offline-state",
                "reference_time": reference_time.isoformat(),
                "caveat": "Timeline filters are deterministic local UI state; no user-specific persistence is implied.",
            }
        )
    return rows


def _compare_windows(markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    marker_count = len(markers)
    return [
        {
            "window_id": "previous_24h",
            "label": "Previous 24h vs current 24h",
            "status": "schema-ready/offline-state",
            "available": marker_count > 0,
            "requires_persistence": False,
            "before_hours": 24,
            "after_hours": 24,
            "marker_count": marker_count,
            "caveat": "Compare state is local to the browser/session and is not saved.",
        },
        {
            "window_id": "previous_7d",
            "label": "Previous 7d vs current 7d",
            "status": "schema-ready/offline-state",
            "available": marker_count > 0,
            "requires_persistence": False,
            "before_hours": 168,
            "after_hours": 168,
            "marker_count": marker_count,
            "caveat": "Longer comparisons use the currently loaded fixture/runtime rows only.",
        },
        {
            "window_id": "saved_compare_session",
            "label": "Saved compare session",
            "status": "unavailable",
            "available": False,
            "requires_persistence": True,
            "before_hours": None,
            "after_hours": None,
            "marker_count": 0,
            "caveat": "Saved compare windows require a later persistence/auth slice.",
        },
    ]


def _provider_requirements(layers: list[dict[str, Any]], provider_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    provider_status_by_name = {
        str(row.get("provider") or row.get("source") or "").lower(): _normalize_status(row.get("status") or row.get("source_status"))
        for row in provider_rows
    }
    for layer in layers:
        provider = str(layer.get("provider") or "none")
        status = _normalize_status(layer.get("source_status"))
        provider_status = provider_status_by_name.get(provider.lower(), status)
        rows.append(
            {
                "requirement_id": f"layer:{layer['layer_id']}",
                "layer_id": layer["layer_id"],
                "provider": provider,
                "provider_status": provider_status,
                "layer_status": status,
                "availability": layer.get("availability"),
                "requires_key": layer.get("requires_key"),
                "row_count": layer.get("row_count"),
                "fresh_or_cached_required_for_live": True,
                "live_claim_allowed": provider_status in {"live/fresh", "cached"} and status in {"live/fresh", "cached"},
                "recommended_action": layer.get("recommended_action") or recommended_action_for_status(status),
                "caveat": layer.get("caveat") or "",
            }
        )
    rows.extend(
        [
            {
                "requirement_id": "capability:live_ais",
                "layer_id": "ais_unavailable",
                "provider": "none",
                "provider_status": "unavailable",
                "layer_status": "unavailable",
                "availability": "unavailable",
                "requires_key": "AIS_PROVIDER_KEY",
                "row_count": 0,
                "fresh_or_cached_required_for_live": True,
                "live_claim_allowed": False,
                "recommended_action": "Keep live vessel layers unavailable until a real AIS provider is configured and probed.",
                "caveat": "No live AIS or vessel tracking is claimed.",
            },
            {
                "requirement_id": "capability:live_sanctions",
                "layer_id": "sanctions",
                "provider": "opensanctions",
                "provider_status": "unavailable",
                "layer_status": "unavailable",
                "availability": "unavailable",
                "requires_key": None,
                "row_count": 0,
                "fresh_or_cached_required_for_live": True,
                "live_claim_allowed": False,
                "recommended_action": "Build a reviewed OpenSanctions source path before rendering sanctions markers.",
                "caveat": "Sanctions are registry-ready only in this slice.",
            },
        ]
    )
    return rows


def _readiness() -> dict[str, Any]:
    unavailable = [
        {
            "capability": "live_ais_tracking",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "recommended_action": "Keep live vessel positions unavailable until a reviewed AIS provider is wired and probed.",
            "caveat": "No live AIS or vessel-flow telemetry is available in Phase 4.",
        },
        {
            "capability": "live_flight_tracking",
            "status": "unavailable",
            "source_status": "missing-key",
            "provider": "opensky",
            "recommended_action": "Configure OpenSky credentials and verify state-vector fetches before enabling live flight markers.",
            "caveat": "Flight layers stay unavailable unless provider evidence is fresh or cached.",
        },
        {
            "capability": "live_sanctions_markers",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "opensanctions",
            "recommended_action": "Add reviewed source-backed sanctions ingestion before markers are shown.",
            "caveat": "No sanctions markers are rendered as live in Phase 4.",
        },
        {
            "capability": "saved_compare_windows",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "recommended_action": "Add authenticated persistence in a later slice before saving compare sessions.",
            "caveat": "Compare windows are schema-ready local state only.",
        },
        {
            "capability": "broker_execution",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "recommended_action": "Keep the map read-only and non-advisory.",
            "caveat": "No broker execution, order routing, or market-action pathway is added.",
        },
        {
            "capability": "auth_billing_user_accounts",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "recommended_action": "Defer accounts, billing, and user state to a later commercial slice.",
            "caveat": "No auth, billing, hosted persistence, or user-specific state is added.",
        },
        {
            "capability": "graph_database_dependency",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "recommended_action": "Keep Phase 2F graph context as first-party JSON until persistence is reviewed.",
            "caveat": "No graph database dependency is added.",
        },
    ]
    return {
        "map_mode": "fixture-safe/source-status-aware",
        "compare_windows": "schema-ready/offline-state",
        "live_ais_added": False,
        "live_flight_tracking_added": False,
        "live_sanctions_added": False,
        "broker_execution_added": False,
        "auth_added": False,
        "billing_added": False,
        "hosted_persistence_added": False,
        "graph_database_dependency_added": False,
        "paid_provider_dependency_added": False,
        "unavailable_capabilities": unavailable,
    }


def _summary(markers: list[dict[str, Any]], layers: list[dict[str, Any]], compare_windows: list[dict[str, Any]]) -> dict[str, Any]:
    coordinate_counts: dict[str, int] = {}
    layer_status_counts: dict[str, int] = {}
    for marker in markers:
        coordinate_counts[marker["coordinate_status"]] = coordinate_counts.get(marker["coordinate_status"], 0) + 1
    for layer in layers:
        status = str(layer.get("source_status") or "unknown")
        layer_status_counts[status] = layer_status_counts.get(status, 0) + 1
    return {
        "marker_count": len(markers),
        "visible_marker_count": len(markers),
        "source_backed_marker_count": sum(1 for marker in markers if marker["source_status"] in {"live/fresh", "cached", "fresh"}),
        "fixture_marker_count": sum(1 for marker in markers if marker["source_status"] == "fixture"),
        "approximate_coordinate_count": coordinate_counts.get("approximate", 0),
        "fixture_coordinate_count": coordinate_counts.get("fixture", 0),
        "static_coordinate_count": coordinate_counts.get("static/proxy", 0),
        "unavailable_coordinate_count": coordinate_counts.get("unavailable", 0),
        "layer_count": len(layers),
        "live_or_cached_layer_count": sum(1 for layer in layers if layer["source_status"] in {"live/fresh", "cached"}),
        "proxy_static_layer_count": layer_status_counts.get("proxy/static", 0),
        "unavailable_layer_count": sum(1 for layer in layers if layer["availability"] == "unavailable"),
        "compare_window_count": len(compare_windows),
        "saved_compare_persistence_available": False,
        "non_advisory": True,
        "live_ais_claimed": False,
        "live_flight_tracking_claimed": False,
        "live_sanctions_claimed": False,
        "broker_execution_added": False,
        "auth_added": False,
        "billing_added": False,
        "hosted_persistence_added": False,
        "graph_database_dependency_added": False,
        "external_source_copied": False,
    }


def build_war_room_map_contract(
    *,
    state: dict[str, Any] | None = None,
    events: Any = None,
    layer_runtime: dict[str, Any] | None = None,
    provider_rows: Any = None,
    event_graph: dict[str, Any] | None = None,
    max_markers: int = 80,
) -> dict[str, Any]:
    """Build a map-first War Room contract from existing source/status payloads."""
    if state is None and events is None and layer_runtime is None:
        from .war_room import build_war_room_state

        state = build_war_room_state(include_default_runtime=False)
    source_state = state or {}
    event_rows = dedupe_events(events if events is not None else source_state.get("events"))[:max_markers]
    raw_layer_payload = layer_runtime or source_state.get("layer_runtime_status") or build_layer_runtime_payload()
    raw_layers = _records(raw_layer_payload.get("layers") if isinstance(raw_layer_payload, dict) else raw_layer_payload)
    layers = [_build_layer(row) for row in raw_layers]
    graph = event_graph or build_event_asset_graph_contract(events=event_rows, provider_rows=provider_rows)
    markers = [marker for row in event_rows if (marker := _build_marker(row, layers, graph)) is not None]
    markers = sorted(markers, key=lambda item: (item["severity_score"], item["timestamp"]), reverse=True)
    for layer in layers:
        layer_id = str(layer.get("layer_id") or "")
        layer["visible_marker_count"] = sum(1 for marker in markers if layer_id in marker.get("layer_ids", []))
    timeline_filters = _timeline_filters(markers)
    compare_windows = _compare_windows(markers)
    providers = _records(provider_rows)
    provider_requirements = _provider_requirements(layers, providers)
    readiness = _readiness()
    return {
        "war_room_map_version": WAR_ROOM_MAP_VERSION,
        "markers": markers,
        "layers": layers,
        "timeline_filters": timeline_filters,
        "compare_windows": compare_windows,
        "provider_requirements": provider_requirements,
        "readiness": readiness,
        "evidence_refs": EVIDENCE_REFS,
        "summary": _summary(markers, layers, compare_windows),
        "caveat": NON_ADVISORY_CAVEAT,
    }
