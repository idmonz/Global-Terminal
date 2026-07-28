from __future__ import annotations
from pathlib import Path
from typing import Any
from .research_workspace_db import execute_query, json_dumps, json_loads, new_id, utc_now


def store_research_artifact(commit_id: str, artifact_type: str, title: str, uri: str = "", payload: dict[str, Any] | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
    row = {"artifact_id": new_id("artifact"), "commit_id": commit_id, "artifact_type": artifact_type, "title": title, "uri": uri, "payload_json": json_dumps(payload or {}), "created_at": utc_now()}
    execute_query("INSERT INTO strategy_artifacts (artifact_id, commit_id, artifact_type, title, uri, payload_json, created_at) VALUES (:artifact_id, :commit_id, :artifact_type, :title, :uri, :payload_json, :created_at)", row, db_path=db_path)
    row["payload_json"] = payload or {}
    return row


def list_research_artifacts(commit_id: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    rows = execute_query("SELECT * FROM strategy_artifacts WHERE commit_id = ? ORDER BY created_at DESC", (commit_id,), fetch=True, db_path=db_path)
    out=[]
    for r in rows:  # type: ignore[union-attr]
        d=dict(r); d["payload_json"]=json_loads(d.get("payload_json"),{}); out.append(d)
    return out

