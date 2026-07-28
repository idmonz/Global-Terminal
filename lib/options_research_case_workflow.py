from __future__ import annotations
from typing import Any

from .options_research_case_store import (
    build_case_timeline,
    create_options_research_case,
    export_case_manifest_redacted,
    load_options_research_case,
    save_chain_snapshot_to_case,
    save_option_book_stress_to_case,
    save_quant_diagnostics_to_case,
    save_surface_qa_to_case,
    save_surface_snapshot_to_case,
    update_options_research_case_status,
)
from .options_research_case_index import (
    rebuild_options_case_index,
    search_options_research_cases,
    filter_options_cases_by_status,
    filter_options_cases_by_underlying,
    filter_options_cases_by_tag,
    build_options_case_index_summary,
    export_options_case_index_redacted,
)


def run_options_case_workflow(action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = payload or {}
    action_id = str(action or "").upper()
    base_dir = data.get("base_dir")
    case_id = data.get("case_id")
    if action_id == "CREATE_OPTIONS_RESEARCH_CASE":
        return create_options_research_case(data.get("title", "Options Research Case"), case_id=case_id, base_dir=base_dir, metadata=data.get("metadata"))
    if action_id == "REBUILD_OPTIONS_CASE_INDEX":
        return rebuild_options_case_index(base_dir=base_dir)
    if action_id == "SEARCH_OPTIONS_CASES":
        return {"ok": True, "cases": search_options_research_cases(data.get("query", ""), base_dir=base_dir, limit=data.get("limit", 25)), "research_only": True}
    if action_id == "FILTER_OPTIONS_CASES_BY_STATUS":
        return {"ok": True, "cases": filter_options_cases_by_status(data.get("status", "active"), base_dir=base_dir), "research_only": True}
    if action_id == "FILTER_OPTIONS_CASES_BY_UNDERLYING":
        return {"ok": True, "cases": filter_options_cases_by_underlying(data.get("underlying", ""), base_dir=base_dir), "research_only": True}
    if action_id == "FILTER_OPTIONS_CASES_BY_TAG":
        return {"ok": True, "cases": filter_options_cases_by_tag(data.get("tag", ""), base_dir=base_dir), "research_only": True}
    if action_id == "BUILD_OPTIONS_CASE_INDEX_SUMMARY":
        return build_options_case_index_summary(base_dir=base_dir)
    if action_id == "EXPORT_OPTIONS_CASE_INDEX":
        return export_options_case_index_redacted(base_dir=base_dir)
    if not case_id:
        return {"ok": False, "error": "case_id_required", "research_only": True}
    if action_id == "SAVE_CHAIN_TO_CASE":
        return save_chain_snapshot_to_case(case_id, data.get("chain_snapshot", {}), base_dir=base_dir)
    if action_id == "SAVE_SURFACE_TO_CASE":
        return save_surface_snapshot_to_case(case_id, data.get("surface_snapshot", {}), base_dir=base_dir)
    if action_id == "SAVE_SURFACE_QA_TO_CASE":
        return save_surface_qa_to_case(case_id, data.get("surface_qa", {}), base_dir=base_dir)
    if action_id == "SAVE_OPTION_BOOK_STRESS_TO_CASE":
        return save_option_book_stress_to_case(case_id, data.get("option_book_stress", {}), base_dir=base_dir)
    if action_id == "SAVE_QUANT_DIAGNOSTICS_TO_CASE":
        return save_quant_diagnostics_to_case(case_id, data.get("quant_diagnostics", {}), base_dir=base_dir)
    if action_id == "LOAD_OPTIONS_RESEARCH_CASE":
        return load_options_research_case(case_id, base_dir=base_dir)
    if action_id == "UPDATE_OPTIONS_CASE_STATUS":
        return update_options_research_case_status(case_id, data.get("status", "active"), base_dir=base_dir, metadata=data.get("metadata"))
    if action_id == "EXPORT_OPTIONS_CASE_MANIFEST":
        return export_case_manifest_redacted(case_id, base_dir=base_dir)
    if action_id == "BUILD_OPTIONS_CASE_TIMELINE":
        return {"ok": True, "case_id": case_id, "timeline": build_case_timeline(case_id, base_dir=base_dir), "research_only": True}
    return {"ok": False, "error": "unsupported_case_workflow", "action": action_id, "research_only": True}
