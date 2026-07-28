from __future__ import annotations

from typing import Any

from .options_greeks import calculate_greeks
from .options_iv_solver import implied_volatility
from .options_lab_visuals import build_greeks_table, build_options_price_card, build_scenario_table_payload
from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE
from .options_pricing_models import price_option
from .options_provider_capabilities import inspect_options_provider_capabilities
from .options_scenarios import option_scenario_grid
from .options_strategy_templates import list_option_strategy_templates
from .quant_model_lab import build_quant_model_lab_payload
from .options_chain_ingestion import build_option_chain_snapshot
from .options_chain_iv import build_chain_iv_snapshot
from .options_vol_surface import build_vol_surface_snapshot
from .options_surface_quality import build_surface_quality_score
from .options_surface_diff import build_surface_snapshot_diff
from .options_book_stress import build_option_book_stress_snapshot
from .quant_diagnostics_report import build_quant_diagnostics_snapshot
from .options_research_case_store import list_options_research_cases, load_options_research_case, export_case_manifest_redacted
from .options_research_case_visuals import build_options_case_selector_payload, build_options_case_timeline_panel
from .options_research_case_index import build_options_case_index_summary, search_options_research_cases, export_options_case_index_redacted
from .options_surface_review_store import build_persistent_surface_review_queue, load_surface_review_item, export_surface_review_queue_redacted
from .actionless_simulation_index import build_simulation_case_index_summary, search_simulation_cases, export_simulation_case_index_redacted
from .actionless_simulation_store import export_simulation_case_redacted
from .model_artifact_governance import build_external_model_placeholder_cards, build_model_artifact_registry_summary

DEFAULT_OPTION_INPUT = {
    "option_type": "call",
    "underlying_price": 100.0,
    "strike": 100.0,
    "time_to_expiry_years": 1.0,
    "risk_free_rate": 0.05,
    "dividend_yield": 0.0,
    "volatility": 0.20,
    "contract_multiplier": 100.0,
    "premium": 10.45,
    "model": "black_scholes",
}


def build_options_lab_page_payload(input_data: dict[str, Any] | None = None, *, demo_mode: bool = False, chain_rows: list[dict[str, Any]] | None = None, option_book_positions: list[dict[str, Any]] | None = None, quant_series: dict[str, list[float]] | None = None, previous_surface: dict[str, Any] | None = None, selected_case_id: str | None = None, selected_review_id: str | None = None, case_base_dir: str | None = None, case_search_query: str = "", selected_simulation_case_id: str | None = None, simulation_base_dir: str | None = None, simulation_search_query: str = "") -> dict[str, Any]:
    data = {**DEFAULT_OPTION_INPUT, **(input_data or {})} if demo_mode or input_data else dict(DEFAULT_OPTION_INPUT)
    pricing = price_option(data)
    greeks = calculate_greeks(data)
    iv = implied_volatility(data, market_price=data.get("premium"))
    scenario = option_scenario_grid(data, price_grid=[80, 90, 100, 110, 120], volatility_grid=[0.15, 0.20, 0.25], time_grid=[data["time_to_expiry_years"]], rate_grid=[data["risk_free_rate"]])

    chain_snapshot = build_option_chain_snapshot(rows=chain_rows or []) if chain_rows else None
    iv_snapshot = build_chain_iv_snapshot(chain_snapshot) if chain_snapshot else None
    surface = build_vol_surface_snapshot(iv_snapshot) if iv_snapshot else None
    surface_diff = build_surface_snapshot_diff(previous_surface, surface) if previous_surface and surface else None
    book_stress = build_option_book_stress_snapshot(option_book_positions or []) if option_book_positions else None
    quant_diag = build_quant_diagnostics_snapshot(quant_series) if quant_series else None
    cases = list_options_research_cases(base_dir=case_base_dir)
    case_index_summary = build_options_case_index_summary(base_dir=case_base_dir)
    case_search_payload = {"query": case_search_query, "results": search_options_research_cases(case_search_query, base_dir=case_base_dir), "research_only": True}
    review_queue_summary = build_persistent_surface_review_queue(base_dir=case_base_dir)
    selected_case = None
    if selected_case_id:
        try:
            # Use the redacted export in the page payload so private local paths never leak into UI JSON.
            selected_case = export_case_manifest_redacted(selected_case_id, base_dir=case_base_dir)
        except Exception:
            selected_case = {"case_id": selected_case_id, "error": "case_not_found", "research_only": True}
    selected_review_item = None
    if selected_review_id:
        try:
            selected_review_item = load_surface_review_item(selected_review_id, base_dir=case_base_dir)
        except Exception:
            selected_review_item = {"review_id": selected_review_id, "error": "review_item_not_found", "research_only": True}
    simulation_index_summary = {"ok": True, "case_count": 0, "by_status": {}, "private_storage": True, "actionless": True, "research_only": True}
    simulation_search_payload = {"query": simulation_search_query, "results": [], "actionless": True, "research_only": True}
    simulation_index_export = {"version": 1, "case_count": 0, "entries": [], "export_redacted": True, "private_paths_redacted": True, "actionless": True, "research_only": True}
    selected_simulation_case = None
    if simulation_base_dir or selected_simulation_case_id or simulation_search_query:
        simulation_index_summary = build_simulation_case_index_summary(base_dir=simulation_base_dir)
        simulation_search_payload = {"query": simulation_search_query, "results": search_simulation_cases(simulation_search_query, base_dir=simulation_base_dir), "actionless": True, "research_only": True}
        simulation_index_export = export_simulation_case_index_redacted(base_dir=simulation_base_dir)
    if selected_simulation_case_id:
        try:
            selected_simulation_case = export_simulation_case_redacted(selected_simulation_case_id, base_dir=simulation_base_dir)
        except Exception:
            selected_simulation_case = {"case_id": selected_simulation_case_id, "error": "simulation_case_not_found", "actionless": True, "research_only": True}
    model_governance_cards = build_external_model_placeholder_cards()
    model_registry_summary = build_model_artifact_registry_summary(model_governance_cards)

    return {
        "notice": RESEARCH_ONLY_OPTIONS_NOTICE,
        "demo_mode": bool(demo_mode),
        "demo_mode_label": "Demo data is isolated and explicitly labeled." if demo_mode else "User-supplied mode; no demo chain/book/series is loaded by default.",
        "sections": [
            "Research Case selector",
            "Create new options case",
            "Save uploaded chain to case",
            "Save surface snapshot to case",
            "Save surface QA to review queue",
            "Save option-book stress to case",
            "Save quant diagnostics to case",
            "Attach selected case to report",
            "Attach selected case to StrategyCommit",
            "Case timeline panel",
            "Case index summary",
            "Case search/filter payload",
            "Persistent surface review queue",
            "Selected review item panel",
            "Action-less simulation case index",
            "Selected action-less simulation case",
            "Scenario set and feed datasheet governance",
            "Model artifact governance cards",
            "Redacted simulation export actions",
            "Research-only notice",
            "Option pricing calculator",
            "Greeks panel",
            "Implied volatility solver",
            "Payoff/scenario explorer",
            "Strategy payoff templates",
            "Source/provider caveat panel",
            "Uploaded Chain Snapshot",
            "Chain Quality",
            "IV Diagnostics",
            "Surface QA",
            "Surface Diff",
            "Option Book Stress",
            "Quant Diagnostics",
            "Report / Attachments",
            "Raw payload expander only",
        ],
        "source_chips": {"chain": "user_supplied" if chain_snapshot else "not_supplied", "book": "user_supplied" if book_stress else "not_supplied", "quant": "user_supplied" if quant_diag else "not_supplied", "case": "selected" if selected_case else "not_selected", "simulation_case": "selected" if selected_simulation_case else "not_selected", "freshness": "manual_or_user_supplied"},
        "case_selector": build_options_case_selector_payload(cases),
        "case_index_summary": case_index_summary,
        "case_search_filter_payload": case_search_payload,
        "case_index_export_redacted": export_options_case_index_redacted(base_dir=case_base_dir),
        "selected_case": selected_case,
        "case_timeline_panel": build_options_case_timeline_panel(selected_case) if selected_case and not selected_case.get("error") else None,
        "persistent_surface_review_queue_summary": review_queue_summary,
        "surface_review_queue_export_redacted": export_surface_review_queue_redacted(base_dir=case_base_dir),
        "selected_review_item_panel": selected_review_item,
        "actionless_simulation_case_index_summary": simulation_index_summary,
        "actionless_simulation_search_payload": simulation_search_payload,
        "actionless_simulation_index_export_redacted": simulation_index_export,
        "selected_actionless_simulation_case": selected_simulation_case,
        "model_artifact_governance_cards": model_governance_cards,
        "model_artifact_registry_summary": model_registry_summary,
        "simulation_case_actions": ["CREATE_SIMULATION_CASE", "UPDATE_SIMULATION_CASE", "SAVE_SCENARIO_SET", "SAVE_DATA_FEED_SNAPSHOT", "SAVE_MODEL_ARTIFACT_CARD", "SAVE_SIMULATION_RESULT", "SAVE_SIMULATION_REVIEW_ITEM", "UPDATE_SIMULATION_REVIEW_STATUS"],
        "simulation_redacted_export_actions": ["BUILD_SIMULATION_CASE_INDEX", "SEARCH_SIMULATION_CASES", "EXPORT_SIMULATION_CASE_INDEX", "EXPORT_SIMULATION_CASE_REDACTED"],
        "simulation_attachment_actions": ["ATTACH_SIMULATION_TO_REPORT", "ATTACH_SIMULATION_TO_STRATEGY_COMMIT"],
        "case_to_report_actions": ["EXPORT_OPTIONS_CASE_MANIFEST", "EXPORT_OPTIONS_CASE_INDEX"],
        "case_to_strategy_commit_actions": ["ATTACH_OPTIONS_RESULT_TO_STRATEGY_COMMIT", "ATTACH_MODEL_SNAPSHOT_TO_STRATEGY_COMMIT"],
        "persistent_review_actions": ["SAVE_SURFACE_REVIEW_ITEM", "LIST_SURFACE_REVIEW_QUEUE", "UPDATE_PERSISTENT_SURFACE_REVIEW_STATUS"],
        "input": data,
        "pricing": pricing,
        "price_card": build_options_price_card(pricing),
        "greeks": greeks,
        "greeks_table": build_greeks_table(greeks),
        "iv_solver": iv,
        "scenario": scenario,
        "scenario_table": build_scenario_table_payload(scenario),
        "strategy_templates": list_option_strategy_templates(),
        "provider_caveats": inspect_options_provider_capabilities(),
        "uploaded_chain_snapshot": chain_snapshot,
        "chain_quality": chain_snapshot.get("quality") if chain_snapshot else None,
        "iv_diagnostics": iv_snapshot,
        "surface_snapshot": surface,
        "surface_qa": build_surface_quality_score(surface) if surface else None,
        "surface_diff": surface_diff,
        "option_book_stress": book_stress,
        "quant_diagnostics": quant_diag,
        "quant_model_snapshot_panel": build_quant_model_lab_payload(),
        "raw_payload_expanders_only": True,
        "research_only": True,
    }
