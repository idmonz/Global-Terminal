from __future__ import annotations
from pathlib import Path
from typing import Any
from .provider_snapshot_store import get_latest_provider_health_snapshot
from .data_quality_snapshot_store import get_latest_data_quality_snapshot
from .watchlist_alias_registry import normalize_token, aliases_for


def find_provider_snapshot_for_item(item: dict[str, Any], db_path: str | Path | None = None, supplied: dict[str, Any] | None = None) -> dict[str, Any] | None:
    supplied = supplied or {}
    names = [item.get("display_name"), item.get("symbol"), item.get("source")]
    for term in list(names):
        names.extend(list(aliases_for(term)))
    for name in names:
        if not name:
            continue
        for key, value in supplied.items():
            if normalize_token(key) == normalize_token(name):
                return value
        snap = get_latest_provider_health_snapshot(str(name), db_path=db_path)
        if snap:
            return snap
    return get_latest_provider_health_snapshot(db_path=db_path)


def build_provider_context(item: dict[str, Any], db_path: str | Path | None = None, supplied: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = find_provider_snapshot_for_item(item, db_path=db_path, supplied=supplied)
    if not snap:
        return {"source_status": "unavailable", "freshness": "unavailable", "data_confidence": "missing", "provider_snapshot": None, "provider_gaps": ["No provider snapshot stored or supplied."]}
    return {"source_status": snap.get("status", "unknown"), "freshness": snap.get("freshness", "unknown"), "data_confidence": snap.get("confidence", "unknown"), "provider_snapshot": snap, "provider_gaps": snap.get("gaps_json") or snap.get("gaps") or [], "missing_keys": snap.get("missing_keys", [])}


def build_data_quality_context(scope: str = "workspace", db_path: str | Path | None = None) -> dict[str, Any]:
    snap = get_latest_data_quality_snapshot(scope, db_path=db_path) or get_latest_data_quality_snapshot(db_path=db_path)
    if not snap:
        return {"status": "unavailable", "freshness": "unavailable", "data_confidence": "missing", "gaps": []}
    return {"status": snap.get("status"), "freshness": snap.get("freshness"), "data_confidence": snap.get("confidence"), "gaps": snap.get("gaps_json", []), "snapshot": snap}
