from __future__ import annotations

from pathlib import Path
from typing import Any

from .options_attachment_bridge import build_options_attachment
from .research_artifact_store import store_research_artifact
from .strategy_decision_log import get_strategy_commit


def attach_options_result_to_strategy_commit(commit_id: str, result: dict[str, Any], *, db_path: str | Path | None = None) -> dict[str, Any]:
    commit = get_strategy_commit(commit_id, db_path=db_path)
    if not commit:
        return {"ok": False, "error": "strategy_commit_not_found", "commit_id": commit_id, "research_only": True}
    attachment = build_options_attachment(result)
    artifact = store_research_artifact(commit_id, "option_analysis_snapshot", attachment.get("title", "Options result"), payload=attachment, db_path=db_path)
    return {"ok": True, "commit_id": commit_id, "artifact": artifact, "attachment": attachment, "research_only": True}
