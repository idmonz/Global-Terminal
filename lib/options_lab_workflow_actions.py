from __future__ import annotations

from pathlib import Path
from typing import Any

from .options_attachment_bridge import attach_options_result_to_report
from .options_provider_capabilities import inspect_options_provider_capabilities
from .options_report_generator import generate_options_iv_report, generate_options_payoff_report, generate_options_pricing_report, generate_options_scenario_report
from .options_scenarios import build_payoff_scenario
from .options_strategy_commit_bridge import attach_options_result_to_strategy_commit
from .quant_model_attachment_bridge import attach_model_snapshot_to_strategy_commit
from .quant_model_lab import create_quant_model_snapshot
from .quant_model_report_generator import attach_model_snapshot_to_report
from .options_chain_ingestion import build_option_chain_snapshot
from .options_chain_iv import build_chain_iv_snapshot
from .options_surface_report_generator import generate_options_surface_report, build_options_surface_diff_report
from .options_chain_report_generator import generate_options_chain_report
from .options_book_report_generator import generate_options_book_risk_report
from .options_book_scenario_report import generate_option_book_stress_report
from .options_vol_surface import build_vol_surface_snapshot
from .options_surface_quality import build_surface_quality_score
from .options_book_risk import build_option_book_risk_snapshot
from .quant_diagnostics_report import build_quant_diagnostics_report, build_quant_diagnostics_snapshot
from .quant_diagnostics_attachment_bridge import attach_quant_diagnostics_to_report
from .options_research_case_workflow import run_options_case_workflow
from .options_surface_review_queue import create_surface_review_item, update_surface_review_status, build_surface_review_queue
from .options_surface_review_workflow import attach_surface_review_to_report, attach_surface_review_to_strategy_commit
from .options_surface_review_store import (
    save_surface_review_item,
    list_surface_review_items,
    load_surface_review_item,
    update_persistent_surface_review_status,
    archive_surface_review_item,
    build_persistent_surface_review_queue,
    export_surface_review_queue_redacted,
)
from .actionless_simulation_workflow import ACTIONLESS_SIMULATION_ACTIONS, run_actionless_simulation_workflow


def run_options_lab_action(action: str, payload: dict[str, Any] | None = None, *, db_path: str | Path | None = None) -> dict[str, Any]:
    action_id = str(action or "").upper().strip()
    data = payload or {}
    if action_id == "PRICE_OPTION":
        return generate_options_pricing_report(data.get("input", data), persist=False)
    if action_id == "SOLVE_IV":
        return generate_options_iv_report(data.get("input", data), market_price=data.get("market_price"), persist=False)
    if action_id == "PAYOFF_SCENARIO":
        return build_payoff_scenario(data.get("legs", []), data.get("price_grid", []))
    if action_id == "OPTIONS_REPORT":
        return generate_options_pricing_report(data.get("input", data), persist=True, db_path=db_path)
    if action_id == "ATTACH_OPTIONS_RESULT_TO_STRATEGY_COMMIT":
        return attach_options_result_to_strategy_commit(data.get("commit_id", ""), data.get("result", {}), db_path=db_path)
    if action_id == "CREATE_QUANT_MODEL_SNAPSHOT":
        return create_quant_model_snapshot(data.get("model_id", "option_pricing_core"), values=data.get("values"), inputs=data.get("inputs"))
    if action_id == "ATTACH_MODEL_SNAPSHOT_TO_REPORT":
        return attach_model_snapshot_to_report(data.get("snapshot"), db_path=db_path)
    if action_id == "ATTACH_MODEL_SNAPSHOT_TO_STRATEGY_COMMIT":
        return attach_model_snapshot_to_strategy_commit(data.get("commit_id", ""), data.get("snapshot", {}), db_path=db_path)
    if action_id == "INSPECT_OPTIONS_PROVIDER_CAPABILITY":
        return inspect_options_provider_capabilities()
    if action_id == "IMPORT_OPTION_CHAIN_CSV":
        return build_option_chain_snapshot(data.get("csv_text", ""), rows=data.get("rows"), source_label=data.get("source_label"))
    if action_id == "BUILD_VOL_SURFACE_SNAPSHOT":
        chain = data.get("chain_snapshot") or build_option_chain_snapshot(data.get("csv_text", ""), rows=data.get("rows"))
        iv = data.get("iv_snapshot") or build_chain_iv_snapshot(chain)
        return build_vol_surface_snapshot(iv)
    if action_id == "BUILD_OPTION_BOOK_RISK_SNAPSHOT":
        return build_option_book_risk_snapshot(data.get("positions", data.get("rows", [])))
    if action_id == "BUILD_SURFACE_QA":
        surface = data.get("surface_snapshot")
        if surface is None:
            chain = data.get("chain_snapshot") or build_option_chain_snapshot(data.get("csv_text", ""), rows=data.get("rows"))
            surface = build_vol_surface_snapshot(data.get("iv_snapshot") or build_chain_iv_snapshot(chain))
        return build_surface_quality_score(surface)
    if action_id == "BUILD_SURFACE_DIFF":
        return build_options_surface_diff_report(data.get("previous_surface", {}), data.get("current_surface", {}))
    if action_id == "BUILD_OPTION_BOOK_STRESS":
        from .options_book_stress import build_option_book_stress_snapshot
        return build_option_book_stress_snapshot(data.get("positions", data.get("rows", [])))
    if action_id == "OPTIONS_CHAIN_REPORT":
        return generate_options_chain_report(data.get("csv_text"), rows=data.get("rows"), persist=data.get("persist", False), db_path=db_path)
    if action_id == "SURFACE_REPORT":
        iv = data.get("iv_snapshot")
        if iv is None:
            chain = data.get("chain_snapshot") or build_option_chain_snapshot(data.get("csv_text", ""), rows=data.get("rows"))
            iv = build_chain_iv_snapshot(chain)
        return generate_options_surface_report(iv, persist=data.get("persist", False), db_path=db_path)
    if action_id == "OPTION_BOOK_REPORT":
        return generate_options_book_risk_report(data.get("positions", data.get("rows", [])), persist=data.get("persist", False), db_path=db_path)
    if action_id in {"GENERATE_SURFACE_QA_REPORT", "SURFACE_QA_REPORT"}:
        surface = data.get("surface_snapshot")
        if surface is None:
            chain = data.get("chain_snapshot") or build_option_chain_snapshot(data.get("csv_text", ""), rows=data.get("rows"))
            surface = build_vol_surface_snapshot(data.get("iv_snapshot") or build_chain_iv_snapshot(chain))
        return {"ok": True, "report_type": "options_surface_qa_report", "title": "Options Surface QA Report", "quality_score": build_surface_quality_score(surface), "surface_snapshot": surface, "research_only": True}
    if action_id in {"GENERATE_OPTION_BOOK_STRESS_REPORT", "OPTION_BOOK_STRESS_REPORT"}:
        return generate_option_book_stress_report(data.get("positions", data.get("rows", [])), persist=data.get("persist", False), db_path=db_path)
    if action_id in {"RUN_HRP_RMT_DIAGNOSTIC", "RUN_KALMAN_GARCH_DIAGNOSTIC", "GENERATE_QUANT_DIAGNOSTICS_REPORT"}:
        return build_quant_diagnostics_report(data.get("prices_by_asset", {}))
    if action_id == "RUN_LOCAL_QUANT_DIAGNOSTICS":
        return build_quant_diagnostics_report(data.get("prices_by_asset", {}))
    if action_id == "ATTACH_QUANT_DIAGNOSTICS_TO_REPORT":
        return attach_quant_diagnostics_to_report(data.get("prices_by_asset", {}), db_path=db_path)
    if action_id in {"CREATE_OPTIONS_RESEARCH_CASE", "SAVE_CHAIN_TO_CASE", "SAVE_SURFACE_TO_CASE", "SAVE_SURFACE_QA_TO_CASE", "SAVE_OPTION_BOOK_STRESS_TO_CASE", "SAVE_QUANT_DIAGNOSTICS_TO_CASE", "LOAD_OPTIONS_RESEARCH_CASE", "BUILD_OPTIONS_CASE_TIMELINE", "EXPORT_OPTIONS_CASE_MANIFEST", "REBUILD_OPTIONS_CASE_INDEX", "SEARCH_OPTIONS_CASES", "FILTER_OPTIONS_CASES_BY_STATUS", "FILTER_OPTIONS_CASES_BY_UNDERLYING", "FILTER_OPTIONS_CASES_BY_TAG", "BUILD_OPTIONS_CASE_INDEX_SUMMARY", "EXPORT_OPTIONS_CASE_INDEX", "UPDATE_OPTIONS_CASE_STATUS"}:
        return run_options_case_workflow(action_id, data)
    if action_id in ACTIONLESS_SIMULATION_ACTIONS:
        return run_actionless_simulation_workflow(action_id, data, db_path=db_path)
    if action_id == "CREATE_SURFACE_REVIEW_ITEM":
        return create_surface_review_item(data.get("surface_qa", {}), case_id=data.get("case_id", ""), title=data.get("title", "Surface QA Review"))
    if action_id == "UPDATE_SURFACE_REVIEW_STATUS":
        return update_surface_review_status(data.get("review_item", {}), data.get("status", "reviewed"), notes=data.get("notes", ""))
    if action_id == "ATTACH_SURFACE_REVIEW_TO_REPORT":
        return attach_surface_review_to_report(data.get("review_item", {}), db_path=db_path)
    if action_id == "ATTACH_SURFACE_REVIEW_TO_STRATEGY_COMMIT":
        return attach_surface_review_to_strategy_commit(data.get("review_item", {}), data.get("commit_id", ""), db_path=db_path)
    if action_id == "SAVE_SURFACE_REVIEW_ITEM":
        return save_surface_review_item(data.get("review_item") or data.get("surface_qa", {}), base_dir=data.get("base_dir"), case_id=data.get("case_id", ""), title=data.get("title", "Surface QA Review"))
    if action_id == "LIST_SURFACE_REVIEW_QUEUE":
        return build_persistent_surface_review_queue(base_dir=data.get("base_dir"), include_archived=data.get("include_archived", False))
    if action_id == "LOAD_SURFACE_REVIEW_ITEM":
        return load_surface_review_item(data.get("review_id", ""), base_dir=data.get("base_dir"))
    if action_id == "UPDATE_PERSISTENT_SURFACE_REVIEW_STATUS":
        return update_persistent_surface_review_status(data.get("review_id", ""), data.get("status", "reviewed"), notes=data.get("notes", ""), base_dir=data.get("base_dir"))
    if action_id == "ARCHIVE_SURFACE_REVIEW_ITEM":
        return archive_surface_review_item(data.get("review_id", ""), notes=data.get("notes", ""), base_dir=data.get("base_dir"))
    if action_id == "EXPORT_SURFACE_REVIEW_QUEUE":
        return export_surface_review_queue_redacted(base_dir=data.get("base_dir"))
    if action_id == "BUILD_SURFACE_REVIEW_QUEUE":
        if data.get("persistent"):
            return build_persistent_surface_review_queue(base_dir=data.get("base_dir"), include_archived=data.get("include_archived", False))
        return build_surface_review_queue(data.get("items", []))
    return {"ok": False, "error": "unknown_options_lab_action", "action": action_id, "research_only": True}
