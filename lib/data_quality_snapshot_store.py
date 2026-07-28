from __future__ import annotations
from pathlib import Path
from typing import Any
from .research_workspace_db import execute_query, json_dumps, json_loads, new_id, utc_now


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["gaps_json"] = json_loads(out.get("gaps_json"), [])
    out["payload_json"] = json_loads(out.get("payload_json"), {})
    return out


def store_data_quality_snapshot(scope: str = "workspace", *, status: str = "unknown", freshness: str = "unknown", confidence: str = "unknown", gaps: list[Any] | None = None, payload: dict[str, Any] | None = None, db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]:
    payload = {**(payload or {}), **extra}
    row = {"snapshot_id": new_id("dq_snapshot"), "scope": scope, "status": status or str(payload.get("status") or "unknown"), "freshness": freshness or str(payload.get("freshness") or "unknown"), "confidence": confidence or str(payload.get("confidence") or "unknown"), "gaps_json": json_dumps(gaps if gaps is not None else payload.get("gaps", [])), "payload_json": json_dumps(payload), "created_at": utc_now()}
    execute_query("""INSERT INTO data_quality_snapshots (snapshot_id, scope, status, freshness, confidence, gaps_json, payload_json, created_at) VALUES (:snapshot_id, :scope, :status, :freshness, :confidence, :gaps_json, :payload_json, :created_at)""", row, db_path=db_path)
    return _decode(row)


def list_data_quality_snapshots(scope: str | None = None, limit: int = 50, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    if scope:
        rows = execute_query("SELECT * FROM data_quality_snapshots WHERE lower(scope)=lower(?) ORDER BY created_at DESC LIMIT ?", (scope, int(limit)), fetch=True, db_path=db_path)
    else:
        rows = execute_query("SELECT * FROM data_quality_snapshots ORDER BY created_at DESC LIMIT ?", (int(limit),), fetch=True, db_path=db_path)
    return [_decode(r) for r in rows]  # type: ignore[arg-type]


def get_latest_data_quality_snapshot(scope: str | None = None, db_path: str | Path | None = None) -> dict[str, Any] | None:
    rows = list_data_quality_snapshots(scope, limit=1, db_path=db_path)
    return rows[0] if rows else None
