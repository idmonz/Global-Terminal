from __future__ import annotations

from pathlib import Path
from typing import Any

from .actionless_simulation_bridge import attach_simulation_case_to_report, attach_simulation_case_to_strategy_commit
from .actionless_simulation_index import (
    build_simulation_case_index_summary,
    export_simulation_case_index_redacted,
    rebuild_simulation_case_index,
    search_simulation_cases,
)
from .actionless_simulation_schema import ACTIONLESS_SIMULATION_NOTICE, validate_safe_id
from .actionless_simulation_store import (
    create_actionless_simulation_case,
    export_simulation_case_redacted,
    load_actionless_simulation_case,
    save_data_feed_snapshot_to_case,
    save_model_artifact_card_to_case,
    save_scenario_set_to_case,
    save_simulation_result_to_case,
    save_simulation_review_item,
    update_actionless_simulation_case,
    update_simulation_review_status,
)

ACTIONLESS_SIMULATION_ACTIONS = {
    "CREATE_SIMULATION_CASE",
    "UPDATE_SIMULATION_CASE",
    "LOAD_SIMULATION_CASE",
    "SAVE_SCENARIO_SET",
    "SAVE_DATA_FEED_SNAPSHOT",
    "SAVE_MODEL_ARTIFACT_CARD",
    "SAVE_SIMULATION_RESULT",
    "BUILD_SIMULATION_CASE_INDEX",
    "SEARCH_SIMULATION_CASES",
    "BUILD_SIMULATION_CASE_INDEX_SUMMARY",
    "EXPORT_SIMULATION_CASE_INDEX",
    "SAVE_SIMULATION_REVIEW_ITEM",
    "UPDATE_SIMULATION_REVIEW_STATUS",
    "EXPORT_SIMULATION_CASE_REDACTED",
    "ATTACH_SIMULATION_TO_REPORT",
    "ATTACH_SIMULATION_TO_STRATEGY_COMMIT",
}


def _missing_case(action_id: str) -> dict[str, Any]:
    return {"ok": False, "error": "case_id_required", "action": action_id, "actionless": True, "research_only": True}


def _artifact_payload(data: dict[str, Any], key: str) -> dict[str, Any]:
    nested = data.get(key) or data.get("payload")
    if isinstance(nested, dict):
        return nested
    return data


def run_actionless_simulation_workflow(
    action: str,
    payload: dict[str, Any] | None = None,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    data = payload or {}
    action_id = str(action or "").upper().strip()
    base_dir = data.get("base_dir")
    case_id = data.get("case_id")

    if action_id not in ACTIONLESS_SIMULATION_ACTIONS:
        return {"ok": False, "error": "unsupported_actionless_simulation_action", "action": action_id, "actionless": True, "research_only": True}

    try:
        if action_id == "CREATE_SIMULATION_CASE":
            return create_actionless_simulation_case(
                data.get("title", "Action-less Simulation Case"),
                objective=data.get("objective", "Research-only simulation case review."),
                case_id=case_id,
                base_dir=base_dir,
                source_context=data.get("source_context", {}),
                linked_options_case_ids=data.get("linked_options_case_ids", []),
                linked_strategy_commit_ids=data.get("linked_strategy_commit_ids", []),
                caveats=data.get("caveats", []),
            )
        if action_id == "BUILD_SIMULATION_CASE_INDEX":
            return rebuild_simulation_case_index(base_dir=base_dir)
        if action_id == "SEARCH_SIMULATION_CASES":
            return {"ok": True, "cases": search_simulation_cases(data.get("query", ""), base_dir=base_dir, limit=data.get("limit", 25)), "actionless": True, "research_only": True, "notice": ACTIONLESS_SIMULATION_NOTICE}
        if action_id == "BUILD_SIMULATION_CASE_INDEX_SUMMARY":
            return build_simulation_case_index_summary(base_dir=base_dir)
        if action_id == "EXPORT_SIMULATION_CASE_INDEX":
            return export_simulation_case_index_redacted(base_dir=base_dir)

        if not case_id:
            return _missing_case(action_id)

        validate_safe_id(case_id, field_name="case_id")
        if action_id == "UPDATE_SIMULATION_CASE":
            return update_actionless_simulation_case(
                case_id,
                title=data.get("title"),
                objective=data.get("objective"),
                status=data.get("status"),
                source_context=data.get("source_context"),
                linked_options_case_ids=data.get("linked_options_case_ids"),
                linked_strategy_commit_ids=data.get("linked_strategy_commit_ids"),
                caveats=data.get("caveats"),
                base_dir=base_dir,
            )
        if action_id == "LOAD_SIMULATION_CASE":
            return load_actionless_simulation_case(case_id, base_dir=base_dir)
        if action_id == "SAVE_SCENARIO_SET":
            return save_scenario_set_to_case(case_id, _artifact_payload(data, "scenario_set"), base_dir=base_dir)
        if action_id == "SAVE_DATA_FEED_SNAPSHOT":
            return save_data_feed_snapshot_to_case(case_id, _artifact_payload(data, "feed_snapshot"), base_dir=base_dir)
        if action_id == "SAVE_MODEL_ARTIFACT_CARD":
            return save_model_artifact_card_to_case(case_id, _artifact_payload(data, "model_artifact_card"), base_dir=base_dir)
        if action_id == "SAVE_SIMULATION_RESULT":
            return save_simulation_result_to_case(case_id, _artifact_payload(data, "simulation_result"), base_dir=base_dir)
        if action_id == "SAVE_SIMULATION_REVIEW_ITEM":
            return save_simulation_review_item(case_id, _artifact_payload(data, "review_item"), base_dir=base_dir)
        if action_id == "UPDATE_SIMULATION_REVIEW_STATUS":
            review_id = data.get("review_id")
            if not review_id:
                return {"ok": False, "error": "review_id_required", "action": action_id, "actionless": True, "research_only": True}
            return update_simulation_review_status(
                case_id,
                review_id,
                data.get("status", "reviewed"),
                notes=data.get("notes", ""),
                reviewer=data.get("reviewer", ""),
                base_dir=base_dir,
            )
        if action_id == "EXPORT_SIMULATION_CASE_REDACTED":
            return export_simulation_case_redacted(case_id, base_dir=base_dir)
        if action_id == "ATTACH_SIMULATION_TO_REPORT":
            return attach_simulation_case_to_report(case_id, base_dir=base_dir, db_path=db_path)
        if action_id == "ATTACH_SIMULATION_TO_STRATEGY_COMMIT":
            commit_id = data.get("commit_id")
            if not commit_id:
                return {"ok": False, "error": "commit_id_required", "action": action_id, "actionless": True, "research_only": True}
            return attach_simulation_case_to_strategy_commit(case_id, commit_id, base_dir=base_dir, db_path=db_path)
    except Exception as exc:
        return {
            "ok": False,
            "error": "actionless_simulation_validation_failed",
            "action": action_id,
            "message": str(exc),
            "actionless": True,
            "research_only": True,
            "notice": ACTIONLESS_SIMULATION_NOTICE,
        }

    return {"ok": False, "error": "unhandled_actionless_simulation_action", "action": action_id, "actionless": True, "research_only": True}
