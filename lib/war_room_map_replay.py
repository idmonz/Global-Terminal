from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .research_workspace_db import get_connection


SNAPSHOT_VERSION = "war_room_map_snapshot.v1"
REPLAY_VERSION = "war_room_map_replay.v1"
SNAPSHOT_ID_PATTERN = re.compile(r"^mapsnap_[a-f0-9]{20}$")
RUNTIME_MODES = {"cache", "live-if-available", "fixture", "local"}
COLLECTION_LIMITS = {
    "markers": 250,
    "layers": 64,
    "providers": 64,
    "news": 120,
    "assets": 80,
    "source_register": 400,
}
PRIVATE_KEYS = {
    "api_key",
    "authorization",
    "client_secret",
    "password",
    "private_body",
    "raw_payload",
    "token",
    "access_token",
    "db_path",
    "local_path",
}

COLLECTION_FIELDS: dict[str, tuple[str, ...]] = {
    "markers": (
        "marker_id", "event_id", "title", "summary", "lat", "lon", "coordinate_method",
        "coordinate_status", "source_status", "availability", "provider", "source", "source_url",
        "fetched_at", "freshness", "confidence", "severity", "severity_score", "region", "domain",
        "layer_ids", "related_asset_node_ids", "event_graph_node_id", "timestamp", "caveat", "data_gap",
        "not_financial_advice",
    ),
    "layers": (
        "layer_id", "label", "domain", "provider", "source", "source_status", "availability", "row_count",
        "visible_marker_count", "requires_key", "freshness", "latest_fetched_at", "caveat", "data_gap",
        "recommended_action",
    ),
    "providers": (
        "provider", "source", "status", "source_status", "availability", "row_count", "fetched_at",
        "latest_fetched_at", "freshness", "confidence", "recommended_action", "caveat", "data_gap", "error",
    ),
    "news": (
        "event_id", "title", "summary", "provider", "source", "source_url", "url", "published_at", "fetched_at",
        "freshness", "source_status", "confidence", "region", "location", "severity", "coordinate_method",
        "caveat", "data_gap", "match_method", "not_financial_advice",
    ),
    "assets": (
        "id", "symbol", "label", "type", "asset_class", "provider", "source", "source_url", "fetched_at",
        "freshness", "source_status", "confidence", "relationship", "relationship_type", "caveat", "data_gap",
        "not_financial_advice",
    ),
    "source_register": (
        "provider", "source", "source_url", "fetched_at", "latest_fetched_at", "freshness", "source_status",
        "status", "availability", "confidence", "coordinate_method", "caveat", "data_gap", "error", "layer_id",
        "marker_id", "event_id",
    ),
}

IDENTITY_FIELDS = {
    "events": ("marker_id", "event_id", "source_url", "title"),
    "layers": ("layer_id", "label"),
    "providers": ("provider", "source"),
    "news": ("source_url", "url", "event_id", "title"),
    "assets": ("id", "symbol", "label"),
}
VOLATILE_DIFF_FIELDS = {"fetched_at", "latest_fetched_at"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _bounded_scalar(value: Any, *, depth: int = 0) -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else None
    if isinstance(value, str):
        return value[:1200]
    if depth >= 2:
        return str(value)[:1200]
    if isinstance(value, (list, tuple, set)):
        return [_bounded_scalar(item, depth=depth + 1) for item in list(value)[:80]]
    if isinstance(value, dict):
        return {
            str(key)[:80]: _bounded_scalar(item, depth=depth + 1)
            for key, item in list(value.items())[:80]
            if str(key).lower() not in PRIVATE_KEYS
        }
    return str(value)[:1200]


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [dict(value)]
    return []


def _normalize_collection(name: str, rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = COLLECTION_FIELDS[name]
    output: list[dict[str, Any]] = []
    for raw in list(rows)[: COLLECTION_LIMITS[name]]:
        row = {
            field: _bounded_scalar(raw.get(field))
            for field in fields
            if field in raw and field.lower() not in PRIVATE_KEYS
        }
        if row:
            output.append(row)
    identity_fields = IDENTITY_FIELDS.get("events" if name == "markers" else name, fields[:1])
    return sorted(output, key=lambda row: _identity(row, identity_fields))


def _identity(row: dict[str, Any], fields: Iterable[str]) -> str:
    for field in fields:
        value = str(row.get(field) or "").strip()
        if value:
            return f"{field}:{value}"
    encoded = json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"hash:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()[:24]}"


def _status_summary(rows: list[dict[str, Any]], key: str = "source_status") -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get(key) or row.get("status") or row.get("availability") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _extract_snapshot_content(payload: dict[str, Any], runtime_mode: str) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    markers = _normalize_collection("markers", _records(data.get("markers")))
    layers = _normalize_collection("layers", _records(data.get("layer_health")) or _records(data.get("layers")))
    providers = _normalize_collection("providers", _records(data.get("provider_health")))
    news = _normalize_collection("news", _records(data.get("news_rows")) or _records(data.get("related_news")))
    assets = _normalize_collection("assets", _records(data.get("connected_assets")))
    source_register = _normalize_collection("source_register", _records(data.get("source_register")))
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else payload.get("summary") or {}
    source_status = str(summary.get("source_status") or "unknown")
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "runtime_mode": runtime_mode,
        "source_status": source_status,
        "markers": markers,
        "layers": layers,
        "providers": providers,
        "news": news,
        "assets": assets,
        "source_register": source_register,
        "provider_summary": _status_summary(providers),
        "layer_summary": _status_summary(layers),
        "caveat": "Observed local snapshot; rows retain their original source, freshness, coordinate, caveat and data-gap labels.",
    }


def _content_hash(content: dict[str, Any]) -> str:
    encoded = json.dumps(content, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _observed_at(content: dict[str, Any], fallback: datetime) -> str:
    candidates = []
    for row in [*content["markers"], *content["news"]]:
        for key in ("timestamp", "published_at", "fetched_at"):
            parsed = _parse_time(row.get(key))
            if parsed:
                candidates.append(parsed)
    return _iso(max(candidates) if candidates else fallback)


def normalize_snapshot_id(value: Any, *, allow_empty: bool = False) -> str:
    text = str(value or "").strip().lower()
    if allow_empty and not text:
        return ""
    if not SNAPSHOT_ID_PATTERN.fullmatch(text):
        raise ValueError("Invalid map snapshot id.")
    return text


def capture_war_room_map_snapshot(
    payload: dict[str, Any],
    *,
    runtime_mode: str = "cache",
    retention_days: int = 30,
    captured_at: str | datetime | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    mode = str(runtime_mode or "cache").strip().lower()
    if mode not in RUNTIME_MODES:
        raise ValueError("Invalid runtime mode for map snapshot.")
    days = int(retention_days)
    if days < 1 or days > 365:
        raise ValueError("retention_days must be between 1 and 365.")
    captured = captured_at if isinstance(captured_at, datetime) else _parse_time(captured_at)
    captured = (captured or _utc_now()).astimezone(timezone.utc).replace(microsecond=0)
    content = _extract_snapshot_content(payload, mode)
    digest = _content_hash(content)
    snapshot_id = f"mapsnap_{digest[:20]}"
    retention_until = captured + timedelta(days=days)
    counts = {name: len(content[name]) for name in ("markers", "layers", "providers", "news", "assets")}

    with get_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT snapshot_id FROM war_room_map_snapshots WHERE content_hash = ?",
            (digest,),
        ).fetchone()
        if existing:
            row = get_war_room_map_snapshot(str(existing[0]), db_path=db_path, include_payload=False)
            return {**row, "created": False, "deduplicated": True}
        conn.execute(
            """
            INSERT INTO war_room_map_snapshots (
                snapshot_id, snapshot_version, content_hash, captured_at, observed_at, runtime_mode,
                source_status, retention_days, retention_until, marker_count, layer_count, provider_count,
                news_count, asset_count, provider_summary_json, layer_summary_json, markers_json, layers_json,
                providers_json, news_json, assets_json, source_register_json, caveat, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id, SNAPSHOT_VERSION, digest, _iso(captured), _observed_at(content, captured), mode,
                content["source_status"], days, _iso(retention_until), counts["markers"], counts["layers"],
                counts["providers"], counts["news"], counts["assets"], _json(content["provider_summary"]),
                _json(content["layer_summary"]), _json(content["markers"]), _json(content["layers"]),
                _json(content["providers"]), _json(content["news"]), _json(content["assets"]),
                _json(content["source_register"]), content["caveat"], _json({"local_private": True}),
            ),
        )
        conn.commit()
    row = get_war_room_map_snapshot(snapshot_id, db_path=db_path, include_payload=False)
    return {**row, "created": True, "deduplicated": False}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(value) if value not in {None, ""} else fallback
    except (TypeError, ValueError):
        return fallback


def _snapshot_from_row(row: Any, *, include_payload: bool) -> dict[str, Any]:
    data = dict(row)
    output = {
        key: data.get(key)
        for key in (
            "snapshot_id", "snapshot_version", "content_hash", "captured_at", "observed_at", "runtime_mode",
            "source_status", "retention_days", "retention_until", "marker_count", "layer_count", "provider_count",
            "news_count", "asset_count", "caveat",
        )
    }
    output["provider_summary"] = _loads(data.get("provider_summary_json"), {})
    output["layer_summary"] = _loads(data.get("layer_summary_json"), {})
    output["privacy_scope"] = "local-private"
    output["historical_truth"] = "project-captured-observation"
    if include_payload:
        for key, column in (
            ("markers", "markers_json"), ("layers", "layers_json"), ("providers", "providers_json"),
            ("news", "news_json"), ("assets", "assets_json"), ("source_register", "source_register_json"),
        ):
            output[key] = _loads(data.get(column), [])
    return output


def get_war_room_map_snapshot(
    snapshot_id: str,
    *,
    db_path: str | Path | None = None,
    include_payload: bool = True,
) -> dict[str, Any]:
    safe_id = normalize_snapshot_id(snapshot_id)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM war_room_map_snapshots WHERE snapshot_id = ?", (safe_id,)).fetchone()
    if not row:
        raise KeyError("Map snapshot not found.")
    return _snapshot_from_row(row, include_payload=include_payload)


def list_war_room_map_snapshots(
    *,
    limit: int = 120,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(int(limit), 365))
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM war_room_map_snapshots ORDER BY captured_at DESC, snapshot_id DESC LIMIT ?",
            (bounded_limit,),
        ).fetchall()
    return [_snapshot_from_row(row, include_payload=False) for row in rows]


def prune_expired_war_room_map_snapshots(
    *,
    as_of: str | datetime | None = None,
    db_path: str | Path | None = None,
) -> int:
    current = as_of if isinstance(as_of, datetime) else _parse_time(as_of)
    current = (current or _utc_now()).astimezone(timezone.utc).replace(microsecond=0)
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM war_room_map_snapshots WHERE retention_until < ?", (_iso(current),))
        conn.commit()
        return int(cursor.rowcount)


def _diff_collection(kind: str, before: list[dict[str, Any]], after: list[dict[str, Any]]) -> dict[str, Any]:
    fields = IDENTITY_FIELDS[kind]
    before_map = {_identity(row, fields): row for row in before}
    after_map = {_identity(row, fields): row for row in after}
    added = [{"identity": key, "after": after_map[key]} for key in sorted(after_map.keys() - before_map.keys())]
    removed = [{"identity": key, "before": before_map[key]} for key in sorted(before_map.keys() - after_map.keys())]
    changed = []
    unchanged_count = 0
    refresh_only_count = 0
    for key in sorted(before_map.keys() & after_map.keys()):
        left = before_map[key]
        right = after_map[key]
        if left == right:
            unchanged_count += 1
            continue
        differing_fields = {field for field in set(left) | set(right) if left.get(field) != right.get(field)}
        ignored_fields = set(VOLATILE_DIFF_FIELDS)
        if kind == "events" and all(
            any(token in str(row.get("source_status") or "").lower() for token in ("proxy", "static", "fixture"))
            for row in (left, right)
        ):
            ignored_fields.add("timestamp")
        changed_fields = sorted(differing_fields - ignored_fields)
        if not changed_fields:
            refresh_only_count += 1
            unchanged_count += 1
            continue
        changed.append({"identity": key, "changed_fields": changed_fields, "before": left, "after": right})
    return {
        "kind": kind,
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged_count": unchanged_count,
        "refresh_only_count": refresh_only_count,
        "summary": {"added": len(added), "removed": len(removed), "changed": len(changed), "unchanged": unchanged_count, "refreshed": refresh_only_count},
    }


def diff_war_room_map_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    diffs = {
        "events": _diff_collection("events", list(before.get("markers") or []), list(after.get("markers") or [])),
        "layers": _diff_collection("layers", list(before.get("layers") or []), list(after.get("layers") or [])),
        "providers": _diff_collection("providers", list(before.get("providers") or []), list(after.get("providers") or [])),
        "news": _diff_collection("news", list(before.get("news") or []), list(after.get("news") or [])),
        "assets": _diff_collection("assets", list(before.get("assets") or []), list(after.get("assets") or [])),
    }
    total = {
        key: sum(item["summary"][key] for item in diffs.values())
        for key in ("added", "removed", "changed", "unchanged", "refreshed")
    }
    return {
        "before_snapshot_id": before.get("snapshot_id"),
        "after_snapshot_id": after.get("snapshot_id"),
        "collections": diffs,
        "summary": total,
        "source_preserved": True,
        "caveat": "Diffs compare captured normalized rows; absence does not prove real-world resolution or causality.",
    }


def build_war_room_map_replay_contract(
    *,
    snapshot_id: str | None = None,
    compare_to: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    timeline = list_war_room_map_snapshots(db_path=db_path)
    if not timeline:
        return {
            "war_room_map_replay_version": REPLAY_VERSION,
            "privacy_scope": "local-private",
            "historical_truth": "empty-local-store",
            "snapshots": [],
            "active_snapshot": None,
            "comparison_snapshot": None,
            "diff": None,
            "readiness": {"capture_available": True, "replay_available": False, "compare_available": False},
            "caveat": "No local observations have been captured. Current rows are not backfilled as history.",
        }
    active_id = normalize_snapshot_id(snapshot_id, allow_empty=True) or str(timeline[0]["snapshot_id"])
    comparison_id = normalize_snapshot_id(compare_to, allow_empty=True)
    active = get_war_room_map_snapshot(active_id, db_path=db_path)
    comparison = get_war_room_map_snapshot(comparison_id, db_path=db_path) if comparison_id else None
    diff = diff_war_room_map_snapshots(comparison, active) if comparison else None
    return {
        "war_room_map_replay_version": REPLAY_VERSION,
        "privacy_scope": "local-private",
        "historical_truth": "project-captured-observations-only",
        "snapshots": timeline,
        "active_snapshot": active,
        "comparison_snapshot": comparison,
        "diff": diff,
        "readiness": {
            "capture_available": True,
            "replay_available": True,
            "compare_available": len(timeline) >= 2,
            "snapshot_count": len(timeline),
        },
        "caveat": "Replay contains only project-captured observations; it does not reconstruct uncaptured history.",
    }


def build_demo_war_room_map_replay_contract() -> dict[str, Any]:
    base = {
        "snapshot_version": SNAPSHOT_VERSION,
        "runtime_mode": "fixture",
        "source_status": "fixture",
        "privacy_scope": "deterministic-public-fixture",
        "historical_truth": "fictional-demo",
        "retention_days": None,
        "retention_until": None,
        "providers": [{"provider": "demo_fixture", "source_status": "fixture", "availability": "limited", "caveat": "Fictional demo provider."}],
        "layers": [{"layer_id": "earthquakes", "label": "Earthquakes", "provider": "demo_fixture", "source_status": "fixture", "availability": "limited", "row_count": 1, "caveat": "Fictional demo layer."}],
        "news": [],
        "assets": [],
        "source_register": [{"provider": "demo_fixture", "source": "fictional-demo", "source_status": "fixture", "caveat": "Not observed history."}],
        "provider_summary": {"fixture": 1},
        "layer_summary": {"fixture": 1},
        "caveat": "Fictional deterministic replay fixture; not observed history.",
    }
    before = {
        **base,
        "snapshot_id": "mapsnap_00000000000000000001",
        "content_hash": "0" * 64,
        "captured_at": "2026-06-20T00:00:00+00:00",
        "observed_at": "2026-06-20T00:00:00+00:00",
        "markers": [{"marker_id": "demo:event:alpha", "event_id": "demo-alpha", "title": "Fictional seismic watch", "lat": 35.0, "lon": 139.0, "provider": "demo_fixture", "source": "fictional-demo", "source_url": "fixture", "fetched_at": "2026-06-20T00:00:00+00:00", "timestamp": "2026-06-20T00:00:00+00:00", "source_status": "fixture", "freshness": "fixture", "confidence": 0.5, "coordinate_method": "fixture_coordinates", "coordinate_status": "fixture", "severity": "watch", "region": "Demo Pacific", "layer_ids": ["earthquakes"], "caveat": "Fictional demo marker.", "data_gap": "No live provider evidence.", "not_financial_advice": True}],
    }
    after = {
        **base,
        "snapshot_id": "mapsnap_00000000000000000002",
        "content_hash": "1" * 64,
        "captured_at": "2026-06-21T00:00:00+00:00",
        "observed_at": "2026-06-21T00:00:00+00:00",
        "markers": [
            {**before["markers"][0], "severity": "elevated", "fetched_at": "2026-06-21T00:00:00+00:00", "timestamp": "2026-06-21T00:00:00+00:00"},
            {"marker_id": "demo:event:beta", "event_id": "demo-beta", "title": "Fictional logistics watch", "lat": 29.0, "lon": 32.0, "provider": "demo_fixture", "source": "fictional-demo", "source_url": "fixture", "fetched_at": "2026-06-21T00:00:00+00:00", "timestamp": "2026-06-21T00:00:00+00:00", "source_status": "fixture", "freshness": "fixture", "confidence": 0.4, "coordinate_method": "fixture_coordinates", "coordinate_status": "fixture", "severity": "watch", "region": "Demo Canal", "layer_ids": ["earthquakes"], "caveat": "Fictional demo marker.", "data_gap": "No live provider evidence.", "not_financial_advice": True},
        ],
    }
    diff = diff_war_room_map_snapshots(before, after)
    return {
        "war_room_map_replay_version": REPLAY_VERSION,
        "privacy_scope": "deterministic-public-fixture",
        "historical_truth": "fictional-demo",
        "snapshots": [{key: row[key] for key in ("snapshot_id", "captured_at", "observed_at", "runtime_mode", "source_status", "historical_truth")} for row in (after, before)],
        "active_snapshot": after,
        "comparison_snapshot": before,
        "diff": diff,
        "readiness": {"capture_available": False, "replay_available": True, "compare_available": True, "snapshot_count": 2},
        "caveat": "Fictional deterministic replay fixture. It is not project-captured or live historical evidence.",
    }
