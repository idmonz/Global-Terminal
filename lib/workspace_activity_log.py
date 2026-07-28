from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_workspace_db import execute_query, json_dumps, new_id, utc_now


def log_workspace_activity(
    activity_type: str,
    title: str,
    summary: str = "",
    *,
    linked_object_type: str = "",
    linked_object_id: str = "",
    severity: str = "info",
    metadata: dict[str, Any] | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    now = utc_now()
    row = {
        "activity_id": new_id("act"),
        "activity_type": activity_type,
        "title": title,
        "summary": summary,
        "linked_object_type": linked_object_type,
        "linked_object_id": linked_object_id,
        "severity": severity,
        "created_at": now,
        "metadata_json": json_dumps(metadata or {}),
    }
    execute_query(
        """
        INSERT INTO workspace_activity_log (
            activity_id, activity_type, title, summary, linked_object_type, linked_object_id,
            severity, created_at, metadata_json
        ) VALUES (:activity_id, :activity_type, :title, :summary, :linked_object_type, :linked_object_id,
            :severity, :created_at, :metadata_json)
        """,
        row,
        db_path=db_path,
    )
    return row


def list_workspace_activity(limit: int = 25, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    return execute_query(
        "SELECT * FROM workspace_activity_log ORDER BY created_at DESC LIMIT ?",
        (int(limit),),
        fetch=True,
        db_path=db_path,
    )  # type: ignore[return-value]

