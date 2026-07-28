from __future__ import annotations
from pathlib import Path
from typing import Any
from .research_workspace_db import execute_query, json_dumps, json_loads, new_id, utc_now


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["missing_keys"] = json_loads(out.get("missing_keys"), [])
    out["gaps_json"] = json_loads(out.get("gaps_json"), [])
    out["payload_json"] = json_loads(out.get("payload_json"), {})
    return out


def store_provider_health_snapshot(provider_name: str | None = None, *, status: str = "unknown", freshness: str = "unknown", confidence: str = "unknown", missing_keys: list[str] | None = None, gaps: list[Any] | None = None, payload: dict[str, Any] | None = None, db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]:
    payload = {**(payload or {}), **extra}
    name = provider_name or payload.get("provider_name") or payload.get("provider") or payload.get("source") or "unknown_provider"
    row = {"snapshot_id": new_id("provider_snapshot"), "provider_name": str(name), "status": status or str(payload.get("status") or "unknown"), "freshness": freshness or str(payload.get("freshness") or "unknown"), "confidence": confidence or str(payload.get("confidence") or "unknown"), "missing_keys": json_dumps(missing_keys if missing_keys is not None else payload.get("missing_keys", [])), "gaps_json": json_dumps(gaps if gaps is not None else payload.get("gaps", [])), "payload_json": json_dumps(payload), "created_at": utc_now()}
    execute_query("""INSERT INTO provider_health_snapshots (snapshot_id, provider_name, status, freshness, confidence, missing_keys, gaps_json, payload_json, created_at) VALUES (:snapshot_id, :provider_name, :status, :freshness, :confidence, :missing_keys, :gaps_json, :payload_json, :created_at)""", row, db_path=db_path)
    return _decode(row)


def list_provider_health_snapshots(provider_name: str | None = None, limit: int = 50, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    if provider_name:
        rows = execute_query("SELECT * FROM provider_health_snapshots WHERE lower(provider_name)=lower(?) ORDER BY created_at DESC LIMIT ?", (provider_name, int(limit)), fetch=True, db_path=db_path)
    else:
        rows = execute_query("SELECT * FROM provider_health_snapshots ORDER BY created_at DESC LIMIT ?", (int(limit),), fetch=True, db_path=db_path)
    return [_decode(r) for r in rows]  # type: ignore[arg-type]


def get_latest_provider_health_snapshot(provider_name: str | None = None, db_path: str | Path | None = None) -> dict[str, Any] | None:
    rows = list_provider_health_snapshots(provider_name, limit=1, db_path=db_path)
    return rows[0] if rows else None
