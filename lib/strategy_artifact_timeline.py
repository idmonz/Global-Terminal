from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_artifact_store import list_research_artifacts


def build_strategy_artifact_timeline(commit_id: str | None = None, *, artifacts: list[dict[str, Any]] | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
    rows = artifacts if artifacts is not None else (list_research_artifacts(commit_id, db_path) if commit_id else [])
    events = [
        {
            "artifact_id": row.get("artifact_id"),
            "commit_id": row.get("commit_id"),
            "artifact_type": row.get("artifact_type"),
            "title": row.get("title"),
            "uri": row.get("uri", ""),
            "created_at": row.get("created_at", ""),
            "research_only": True,
        }
        for row in rows or []
    ]
    return {"title": "Artifact timeline", "events": events, "empty": not events, "research_only": True}
