from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_artifact_store import store_research_artifact
from .research_attachment_models import build_research_attachment
from .strategy_decision_log import get_strategy_commit


def build_quant_model_attachment(snapshot: dict[str, Any]) -> dict[str, Any]:
    return build_research_attachment("quant_model_snapshot", snapshot.get("model_name", "Quant model snapshot"), snapshot, {"source": "local_quant_model_lab", "freshness": "snapshot", "confidence": "deterministic-or-placeholder"})


def attach_model_snapshot_to_strategy_commit(commit_id: str, snapshot: dict[str, Any], *, db_path: str | Path | None = None) -> dict[str, Any]:
    commit = get_strategy_commit(commit_id, db_path=db_path)
    if not commit:
        return {"ok": False, "error": "strategy_commit_not_found", "commit_id": commit_id, "research_only": True}
    attachment = build_quant_model_attachment(snapshot)
    artifact = store_research_artifact(commit_id, "quant_model_snapshot", attachment.get("title", "Quant model snapshot"), payload=attachment, db_path=db_path)
    return {"ok": True, "commit_id": commit_id, "attachment": attachment, "artifact": artifact, "research_only": True}
