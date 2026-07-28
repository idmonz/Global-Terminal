from __future__ import annotations

from pathlib import Path
from typing import Any

from .command_palette_suggestions import build_quick_add_payload
from .report_inbox import create_report
from .report_review_workflow import update_report_review_status
from .research_action_results import build_action_error_card, build_action_result_card
from .research_command_safety import build_blocked_research_boundary_card, detect_forbidden_command_intent
from .alert_evaluator import evaluate_alert_with_state, evaluate_all_alerts
from .alert_store import list_alert_events, list_alert_rules
from .research_artifact_store import store_research_artifact
from .research_workspace_db import backup_workspace_db, export_workspace_json
from .watchlist_store import create_watchlist_item, get_watchlist_item, list_watchlist_items
from .workspace_activity_log import log_workspace_activity
from .strategy_decision_log import attach_report_to_commit, attach_watchlist_items_to_commit, create_strategy_commit, get_strategy_commit
from .strategy_review_workflow import update_strategy_review_status
from .options_lab_workflow_actions import run_options_lab_action
from .actionless_simulation_workflow import ACTIONLESS_SIMULATION_ACTIONS

SAFE_RESEARCH_ACTIONS = {
    "ADD_WATCHLIST_ITEM",
    "EVALUATE_ALERTS_NOW",
    "GENERATE_WATCHLIST_BRIEF",
    "GENERATE_PROVIDER_REPORT",
    "GENERATE_WAR_ROOM_BRIEF",
    "GENERATE_ENERGY_BRIEF",
    "GENERATE_STRATEGY_REVIEW",
    "CREATE_STRATEGY_COMMIT",
    "UPDATE_REPORT_REVIEW_STATUS",
    "UPDATE_STRATEGY_REVIEW_STATUS",
    "ATTACH_REPORT_TO_STRATEGY_COMMIT",
    "ATTACH_WATCHLIST_TO_STRATEGY_COMMIT",
    "EXPORT_WORKSPACE_JSON",
    "BACKUP_WORKSPACE_DB",
    "RUN_PROVIDER_PROBE_DRY_RUN",
    "INSPECT_DATA_QUALITY",
    "BUILD_WAR_ROOM_CONTEXT",
    "INSPECT_VIEW_PRESETS",
    "INSPECT_RELEASE_HYGIENE",
    "PRICE_OPTION",
    "SOLVE_IV",
    "PAYOFF_SCENARIO",
    "OPTIONS_REPORT",
    "ATTACH_OPTIONS_RESULT_TO_STRATEGY_COMMIT",
    "CREATE_QUANT_MODEL_SNAPSHOT",
    "ATTACH_MODEL_SNAPSHOT_TO_REPORT",
    "ATTACH_MODEL_SNAPSHOT_TO_STRATEGY_COMMIT",
    "INSPECT_OPTIONS_PROVIDER_CAPABILITY",
    "IMPORT_OPTION_CHAIN_CSV",
    "BUILD_VOL_SURFACE_SNAPSHOT",
    "BUILD_OPTION_BOOK_RISK_SNAPSHOT",
    "OPTIONS_CHAIN_REPORT",
    "SURFACE_REPORT",
    "OPTION_BOOK_REPORT",
    "RUN_LOCAL_QUANT_DIAGNOSTICS",
    "ATTACH_QUANT_DIAGNOSTICS_TO_REPORT",
    "BUILD_SURFACE_QA",
    "BUILD_SURFACE_DIFF",
    "BUILD_OPTION_BOOK_STRESS",
    "RUN_HRP_RMT_DIAGNOSTIC",
    "RUN_KALMAN_GARCH_DIAGNOSTIC",
    "GENERATE_SURFACE_QA_REPORT",
    "GENERATE_OPTION_BOOK_STRESS_REPORT",
    "GENERATE_QUANT_DIAGNOSTICS_REPORT",
    "CREATE_OPTIONS_RESEARCH_CASE",
    "SAVE_CHAIN_TO_CASE",
    "SAVE_SURFACE_TO_CASE",
    "SAVE_SURFACE_QA_TO_CASE",
    "SAVE_OPTION_BOOK_STRESS_TO_CASE",
    "SAVE_QUANT_DIAGNOSTICS_TO_CASE",
    "LOAD_OPTIONS_RESEARCH_CASE",
    "BUILD_OPTIONS_CASE_TIMELINE",
    "EXPORT_OPTIONS_CASE_MANIFEST",
    "CREATE_SURFACE_REVIEW_ITEM",
    "UPDATE_SURFACE_REVIEW_STATUS",
    "ATTACH_SURFACE_REVIEW_TO_REPORT",
    "ATTACH_SURFACE_REVIEW_TO_STRATEGY_COMMIT",
    "REBUILD_OPTIONS_CASE_INDEX",
    "SEARCH_OPTIONS_CASES",
    "UPDATE_OPTIONS_CASE_STATUS",
    "SAVE_SURFACE_REVIEW_ITEM",
    "LIST_SURFACE_REVIEW_QUEUE",
    "UPDATE_PERSISTENT_SURFACE_REVIEW_STATUS",
    "BUILD_OPTIONS_CASE_INDEX_SUMMARY",
    "EXPORT_OPTIONS_CASE_INDEX",
    "LOAD_SURFACE_REVIEW_ITEM",
    "ARCHIVE_SURFACE_REVIEW_ITEM",
    "EXPORT_SURFACE_REVIEW_QUEUE",
    *ACTIONLESS_SIMULATION_ACTIONS,
}

BLOCKED_ACTIONS = {"BROKER_ROUTE", "MARKET_ORDER", "AUTO_REBALANCE", "LIVE_EXECUTION"}


def _extract_command_like_payload_text(payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(payload, dict):
        return []
    texts: list[str] = []
    for key in ("query", "command", "action_text", "prompt", "user_command"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            texts.append(value)
    return texts


def validate_research_workflow_action(action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    action_id = str(action or "").upper().strip()
    if action_id in BLOCKED_ACTIONS or action_id not in SAFE_RESEARCH_ACTIONS:
        return {"ok": False, "error": "unsupported_or_blocked_action", "action": action_id, "research_only": True}
    for text in _extract_command_like_payload_text(payload):
        safety = detect_forbidden_command_intent(text)
        if safety.get("blocked"):
            return {
                "ok": False,
                "error": "forbidden_research_boundary",
                "action": action_id,
                "matched": safety.get("matched", []),
                "safe_query": safety.get("safe_query", ""),
                "research_only": True,
            }
    if action_id in {"BACKUP_WORKSPACE_DB"} and payload and payload.get("requires_confirmation") and not payload.get("confirmed"):
        return {"ok": False, "error": "confirmation_required", "action": action_id, "research_only": True}
    return {"ok": True, "action": action_id, "research_only": True}


def persist_action_to_activity_log(result: dict[str, Any], *, db_path: str | Path | None = None) -> dict[str, Any]:
    if not result.get("ok"):
        return {}
    return log_workspace_activity(
        "workflow_action",
        result.get("title") or result.get("action", "Research action"),
        result.get("message", ""),
        linked_object_type=result.get("object_type", ""),
        linked_object_id=result.get("object_id", ""),
        severity="info",
        metadata={"action": result.get("action"), "source": result.get("source", "manual"), "research_only": True},
        db_path=db_path,
    )


def _result(action: str, **values: Any) -> dict[str, Any]:
    base = {
        "ok": True,
        "action": action,
        "source": "manual",
        "caveat": "Manual research workflow; no market action or background process was triggered.",
        "research_only": True,
    }
    base.update(values)
    return base


def _create_report_for_action(action: str, payload: dict[str, Any], *, db_path: str | Path | None = None) -> dict[str, Any]:
    report_type = {
        "GENERATE_WATCHLIST_BRIEF": "watchlist",
        "GENERATE_PROVIDER_REPORT": "provider_health",
        "GENERATE_WAR_ROOM_BRIEF": "war_room",
        "GENERATE_ENERGY_BRIEF": "energy_geopolitics",
        "GENERATE_STRATEGY_REVIEW": "strategy_review",
    }.get(action, "manual")
    title = payload.get("title") or {
        "GENERATE_WATCHLIST_BRIEF": "Manual Watchlist Research Brief",
        "GENERATE_PROVIDER_REPORT": "Manual Provider Health Report",
        "GENERATE_WAR_ROOM_BRIEF": "Manual War Room Brief",
        "GENERATE_ENERGY_BRIEF": "Manual Energy Route Brief",
        "GENERATE_STRATEGY_REVIEW": "Manual Strategy Review Report",
    }.get(action, "Manual Research Report")
    report = create_report(
        report_type=report_type,
        title=title,
        summary=payload.get("summary", "Generated from an explicit manual workflow action."),
        linked_watchlist_items=payload.get("linked_watchlist_items") or ([payload["watchlist_item_id"]] if payload.get("watchlist_item_id") else []),
        linked_regions=payload.get("linked_regions") or ([payload["region"]] if payload.get("region") else []),
        linked_events=payload.get("linked_events") or ([payload["event_id"]] if payload.get("event_id") else []),
        linked_strategy_commits=payload.get("linked_strategy_commits") or ([payload["commit_id"]] if payload.get("commit_id") else []),
        source_snapshot=payload.get("source_snapshot") or {"freshness": "manual", "confidence": "source-labeled"},
        data_confidence=payload.get("data_confidence", "source-labeled"),
        provider_gaps=payload.get("provider_gaps", []),
        markdown_body=payload.get("markdown_body") or f"# {title}\n\nManual research workflow output.\n\nSource caveats remain attached to this report.\n",
        tags=payload.get("tags", ["manual_workflow", action.lower()]),
        db_path=db_path,
    )
    return _result(action, title=title, message="Report inbox item created.", object_type="report", object_id=report["report_id"], report=report)



def _evaluate_alerts_now(payload: dict[str, Any], *, db_path: str | Path | None = None) -> dict[str, Any]:
    data_context = payload.get("data_context") or payload.get("metric_context") or payload.get("context") or {}
    source_snapshot = payload.get("source_snapshot") or {"freshness": "manual", "confidence": "source-labeled"}
    supplied_rules = payload.get("alert_rules") or payload.get("rules") or []
    db_rules = list_alert_rules(active_only=True, db_path=db_path) if not supplied_rules else []
    rules = supplied_rules or db_rules
    if not data_context:
        return _result(
            "EVALUATE_ALERTS_NOW",
            title="Alert evaluation skipped",
            message="No alert metric context was supplied; no alert events were created.",
            object_type="alert_evaluation",
            object_id="",
            evaluated_alert_rules=len(rules),
            events_created=0,
            skipped_data_gap_count=len(rules),
            triggered_count=0,
            source_snapshot=source_snapshot,
            status="skipped_unavailable",
            caveat="Alert Engine V2 was not run because required metric context was unavailable.",
        )
    before_events = len(list_alert_events(limit=10000, db_path=db_path))
    evaluations: list[dict[str, Any]] = []
    if supplied_rules:
        for rule in supplied_rules:
            evaluations.append(evaluate_alert_with_state(rule, data_context, persist=True, db_path=db_path, store_non_triggered=False))
    else:
        evaluations = [
            evaluate_alert_with_state(rule, data_context, persist=True, db_path=db_path, store_non_triggered=False)
            for rule in db_rules
        ]
    after_events = len(list_alert_events(limit=10000, db_path=db_path))
    events_created = max(0, after_events - before_events)
    triggered_count = sum(1 for row in evaluations if row.get("triggered"))
    skipped = sum(1 for row in evaluations if str(row.get("status", "")).startswith("skipped") or row.get("data_confidence") == "missing")
    return _result(
        "EVALUATE_ALERTS_NOW",
        title="Alert Engine V2 evaluation completed",
        message="Manual alert evaluation used supplied context and persisted only evaluator-created events.",
        object_type="alert_evaluation",
        object_id="",
        evaluated_alert_rules=len(rules),
        events_created=events_created,
        skipped_data_gap_count=skipped,
        triggered_count=triggered_count,
        evaluations=evaluations,
        source_snapshot=source_snapshot,
        caveat="Manual Alert Engine V2 evaluation; no background daemon or external execution was triggered.",
    )

def run_research_workflow_action(action: str, payload: dict[str, Any] | None = None, *, db_path: str | Path | None = None) -> dict[str, Any]:
    payload = payload or {}
    validation = validate_research_workflow_action(action, payload)
    action_id = validation["action"]
    if not validation.get("ok"):
        if validation.get("error") == "forbidden_research_boundary":
            blocked_card = build_blocked_research_boundary_card((payload or {}).get("query") or (payload or {}).get("command") or action_id)
            return {
                "ok": False,
                "status": "blocked",
                "action": action_id,
                "blocked_card": blocked_card,
                "safe_alternatives": blocked_card.get("safe_alternatives", []),
                "caveat": "No workspace mutation was performed because the request crossed the research boundary.",
                "research_only": True,
            }
        return build_action_error_card(action_id, validation.get("error", "blocked"), details=validation)

    try:
        if action_id == "ADD_WATCHLIST_ITEM":
            q = payload.get("query") or payload.get("symbol") or payload.get("display_name") or payload.get("region") or payload.get("provider") or "Research item"
            safety = detect_forbidden_command_intent(str(q))
            if safety.get("blocked"):
                blocked_card = build_blocked_research_boundary_card(str(q))
                return {
                    "ok": False,
                    "status": "blocked",
                    "action": action_id,
                    "blocked_card": blocked_card,
                    "safe_alternatives": blocked_card.get("safe_alternatives", []),
                    "caveat": "No workspace mutation was performed because the request crossed the research boundary.",
                    "research_only": True,
                }
            quick = build_quick_add_payload(str(q)) if payload.get("query") else {}
            item_payload = {**quick, **payload}
            item = create_watchlist_item(
                item_type=item_payload.get("item_type", "topic"),
                symbol=item_payload.get("symbol", ""),
                display_name=item_payload.get("display_name") or item_payload.get("symbol") or str(q),
                asset_class=item_payload.get("asset_class", item_payload.get("item_type", "topic")),
                exchange=item_payload.get("exchange", ""),
                region=item_payload.get("region", ""),
                country=item_payload.get("country", ""),
                tags=item_payload.get("tags", ["manual_workflow"]),
                watch_reason=item_payload.get("watch_reason", "Added through explicit research workflow action."),
                default_command=item_payload.get("default_command", "WATCHLIST"),
                default_page=item_payload.get("default_page", "pages/20_Watchlist_Alerts.py"),
                source="manual_workflow",
                metadata={"workflow_action": action_id, "research_only": True, **item_payload.get("metadata", {})},
                db_path=db_path,
            )
            result = _result(action_id, title="Watchlist item added", message="Local watchlist state updated.", object_type="watchlist_item", object_id=item["item_id"], item=item)
        elif action_id == "EVALUATE_ALERTS_NOW":
            result = _evaluate_alerts_now(payload, db_path=db_path)
        elif action_id in {"GENERATE_WATCHLIST_BRIEF", "GENERATE_PROVIDER_REPORT", "GENERATE_WAR_ROOM_BRIEF", "GENERATE_ENERGY_BRIEF", "GENERATE_STRATEGY_REVIEW"}:
            result = _create_report_for_action(action_id, payload, db_path=db_path)
        elif action_id == "CREATE_STRATEGY_COMMIT":
            commit = create_strategy_commit(
                strategy_id=payload.get("strategy_id", "manual_strategy_candidate"),
                message=payload.get("message", "Manual research snapshot"),
                parent_commit_id=payload.get("parent_commit_id"),
                strategy_config_snapshot=payload.get("strategy_config_snapshot", {}),
                data_quality_snapshot=payload.get("data_quality_snapshot", {}),
                provider_snapshot=payload.get("provider_snapshot", {}),
                linked_watchlist_items=payload.get("linked_watchlist_items", []),
                linked_reports=payload.get("linked_reports", []),
                tags=payload.get("tags", ["manual_workflow"]),
                db_path=db_path,
            )
            result = _result(action_id, title="Strategy commit created", message="Research snapshot recorded with guard metadata.", object_type="strategy_commit", object_id=commit["commit_id"], commit=commit)
        elif action_id == "UPDATE_REPORT_REVIEW_STATUS":
            update = update_report_review_status(payload.get("report_id", ""), payload.get("status", "reviewed"), notes=payload.get("notes", ""), db_path=db_path)
            if not update.get("ok"):
                return build_action_error_card(action_id, update.get("error", "report_update_failed"), details=update)
            result = _result(action_id, title="Report review updated", message="Selected report review state changed.", object_type="report", object_id=payload.get("report_id"), update=update)
        elif action_id == "UPDATE_STRATEGY_REVIEW_STATUS":
            update = update_strategy_review_status(payload.get("commit_id", ""), payload.get("status", "reviewed"), note=payload.get("note", ""), db_path=db_path)
            if not update.get("ok"):
                return build_action_error_card(action_id, update.get("error", "strategy_update_failed"), details=update)
            result = _result(action_id, title="Strategy review updated", message="Selected commit review state changed.", object_type="strategy_commit", object_id=payload.get("commit_id"), update=update)
        elif action_id == "ATTACH_REPORT_TO_STRATEGY_COMMIT":
            commit = attach_report_to_commit(payload.get("commit_id", ""), payload.get("report_id", ""), db_path=db_path)
            if not commit:
                return build_action_error_card(action_id, "commit_or_report_not_found")
            store_research_artifact(commit["commit_id"], "report", f"Attached report {payload.get('report_id', '')}", payload={"report_id": payload.get("report_id"), "research_only": True}, db_path=db_path)
            result = _result(action_id, title="Report attached to strategy commit", message="Artifact timeline updated.", object_type="strategy_commit", object_id=commit["commit_id"], commit=commit)
        elif action_id == "ATTACH_WATCHLIST_TO_STRATEGY_COMMIT":
            item_id = payload.get("watchlist_item_id") or payload.get("item_id")
            item = get_watchlist_item(item_id, db_path) if item_id else None
            commit = attach_watchlist_items_to_commit(payload.get("commit_id", ""), [item_id] if item_id else [], db_path=db_path)
            if not commit or not item:
                return build_action_error_card(action_id, "commit_or_watchlist_item_not_found")
            store_research_artifact(commit["commit_id"], "watchlist", f"Attached watchlist item {item.get('display_name')}", payload={"watchlist_item_id": item_id, "research_only": True}, db_path=db_path)
            result = _result(action_id, title="Watchlist item attached to strategy commit", message="Artifact timeline updated.", object_type="strategy_commit", object_id=commit["commit_id"], commit=commit)
        elif action_id == "EXPORT_WORKSPACE_JSON":
            exported = export_workspace_json(db_path=db_path)
            result = _result(action_id, title="Workspace JSON export prepared", message="Export payload created in memory for the current workspace.", object_type="workspace_export", object_id="workspace", export=exported)
        elif action_id == "BACKUP_WORKSPACE_DB":
            path = backup_workspace_db(destination=payload.get("destination"), db_path=db_path)
            result = _result(action_id, title="Workspace DB backup created", message="Local workspace DB backup created.", object_type="workspace_backup", object_id=str(path), path=str(path))
        elif action_id == "RUN_PROVIDER_PROBE_DRY_RUN":
            result = _result(action_id, title="Provider probe dry run", message="Provider diagnostics route prepared without network probing.", object_type="provider_probe_dry_run", object_id="provider_probe", provider_status=payload.get("provider_status", "not_run"), missing_keys=payload.get("missing_keys", []), source_snapshot=payload.get("source_snapshot", {"freshness": "not-run", "confidence": "dry-run"}), caveat="Dry-run only; no provider request was made.")
        elif action_id == "INSPECT_DATA_QUALITY":
            result = _result(action_id, title="Data quality inspection", message="Data quality caveat payload prepared.", object_type="data_quality", object_id="data_quality", freshness=payload.get("freshness", "unknown"), gaps=payload.get("gaps", ["context_not_supplied"] if not payload else []), caveat="Missing data remains explicitly caveated; no quality score is fabricated.")
        elif action_id == "BUILD_WAR_ROOM_CONTEXT":
            events = payload.get("events", [])
            result = _result(action_id, title="War Room context built", message="Source-labeled War Room context payload prepared.", object_type="war_room_context", object_id="war_room", event_count=len(events), events=events, caveat="Supplied events only; no live stream claim is made.")
        elif action_id == "INSPECT_VIEW_PRESETS":
            from .view_preset_engine import build_view_presets
            result = _result(action_id, title="View presets inspected", message="Preset catalog payload prepared.", object_type="view_presets", object_id="view_presets", presets=build_view_presets(), caveat="Presets organize supplied context; they do not create data.")
        elif action_id == "INSPECT_RELEASE_HYGIENE":
            result = _result(action_id, title="Release hygiene checklist", message="Release exclusion checklist prepared.", object_type="release_hygiene", object_id="release_hygiene", checklist=["external excluded", "private data excluded", "secrets excluded", "cache/log artifacts excluded"], caveat="Checklist payload only; final package validation is performed by build scripts.")

        elif action_id in ACTIONLESS_SIMULATION_ACTIONS or action_id in {"PRICE_OPTION", "SOLVE_IV", "PAYOFF_SCENARIO", "OPTIONS_REPORT", "ATTACH_OPTIONS_RESULT_TO_STRATEGY_COMMIT", "CREATE_QUANT_MODEL_SNAPSHOT", "ATTACH_MODEL_SNAPSHOT_TO_REPORT", "ATTACH_MODEL_SNAPSHOT_TO_STRATEGY_COMMIT", "INSPECT_OPTIONS_PROVIDER_CAPABILITY", "IMPORT_OPTION_CHAIN_CSV", "BUILD_VOL_SURFACE_SNAPSHOT", "BUILD_OPTION_BOOK_RISK_SNAPSHOT", "OPTIONS_CHAIN_REPORT", "SURFACE_REPORT", "OPTION_BOOK_REPORT", "RUN_LOCAL_QUANT_DIAGNOSTICS", "ATTACH_QUANT_DIAGNOSTICS_TO_REPORT", "BUILD_SURFACE_QA", "BUILD_SURFACE_DIFF", "BUILD_OPTION_BOOK_STRESS", "RUN_HRP_RMT_DIAGNOSTIC", "RUN_KALMAN_GARCH_DIAGNOSTIC", "GENERATE_SURFACE_QA_REPORT", "GENERATE_OPTION_BOOK_STRESS_REPORT", "GENERATE_QUANT_DIAGNOSTICS_REPORT", "CREATE_OPTIONS_RESEARCH_CASE", "SAVE_CHAIN_TO_CASE", "SAVE_SURFACE_TO_CASE", "SAVE_SURFACE_QA_TO_CASE", "SAVE_OPTION_BOOK_STRESS_TO_CASE", "SAVE_QUANT_DIAGNOSTICS_TO_CASE", "LOAD_OPTIONS_RESEARCH_CASE", "BUILD_OPTIONS_CASE_TIMELINE", "EXPORT_OPTIONS_CASE_MANIFEST", "CREATE_SURFACE_REVIEW_ITEM", "UPDATE_SURFACE_REVIEW_STATUS", "ATTACH_SURFACE_REVIEW_TO_REPORT", "ATTACH_SURFACE_REVIEW_TO_STRATEGY_COMMIT", "REBUILD_OPTIONS_CASE_INDEX", "SEARCH_OPTIONS_CASES", "UPDATE_OPTIONS_CASE_STATUS", "SAVE_SURFACE_REVIEW_ITEM", "LIST_SURFACE_REVIEW_QUEUE", "UPDATE_PERSISTENT_SURFACE_REVIEW_STATUS", "BUILD_OPTIONS_CASE_INDEX_SUMMARY", "EXPORT_OPTIONS_CASE_INDEX", "LOAD_SURFACE_REVIEW_ITEM", "ARCHIVE_SURFACE_REVIEW_ITEM", "EXPORT_SURFACE_REVIEW_QUEUE"}:
            lab_result = run_options_lab_action(action_id, payload, db_path=db_path)
            result = _result(action_id, title=lab_result.get("title") or action_id.replace("_", " ").title(), message="Options/quant lab research payload prepared.", object_type=lab_result.get("result_type", "options_quant_lab"), object_id=lab_result.get("report_id") or lab_result.get("commit_id") or lab_result.get("model_id", lab_result.get("case_id", lab_result.get("review_id", ""))), payload=lab_result, caveat="Options and quant model lab action produced research objects only.")
        else:
            return build_action_error_card(action_id, "unhandled_action")
    except Exception as exc:
        return build_action_error_card(action_id, "exception", details={"message": str(exc)})

    activity = persist_action_to_activity_log(result, db_path=db_path)
    result["activity"] = activity
    result["card"] = build_action_result_card(result)
    return result


def refresh_workspace_payload_after_action(action_result: dict[str, Any], *, db_path: str | Path | None = None) -> dict[str, Any]:
    return {
        "last_action": action_result,
        "watchlist_count": len(list_watchlist_items(db_path=db_path)),
        "research_only": True,
    }
