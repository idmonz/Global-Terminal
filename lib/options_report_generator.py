from __future__ import annotations

from pathlib import Path
from typing import Any

from .options_greeks import calculate_greeks
from .options_iv_solver import implied_volatility
from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE
from .options_pricing_models import price_option
from .options_provider_capabilities import build_options_source_snapshot
from .options_report_templates import render_options_report_markdown
from .options_result_schema import build_options_result
from .options_scenarios import option_scenario_grid
from .report_inbox import create_report

REPORT_KIND_TO_TYPE = {
    "pricing": "options_pricing_report",
    "scenario": "options_scenario_report",
    "iv": "options_iv_report",
    "payoff": "options_payoff_report",
}


def generate_options_pricing_report(input_data: dict[str, Any], *, db_path: str | Path | None = None, persist: bool = False) -> dict[str, Any]:
    priced = price_option(input_data)
    greeks = calculate_greeks(input_data)
    payload = {**priced, "greeks": greeks["greeks"]}
    source = build_options_source_snapshot("manual", used_for_calculation=True)
    result = build_options_result("pricing", "Options Pricing Report", payload, source, ["Manual/supplied inputs; no live option chain fetched."])
    markdown = render_options_report_markdown("Options Pricing Report", result, report_kind="options_pricing_report")
    if not persist:
        return {**result, "markdown_body": markdown, "report_type": "options_pricing_report"}
    report = create_report(report_type="options_pricing_report", title="Options Pricing Report", summary="Local research-only option pricing calculation.", source_snapshot=source, data_confidence="user-supplied", provider_gaps=[], attachments=[result], markdown_body=markdown, tags=["goal12a", "options", "pricing"], db_path=db_path)
    return {**result, "report": report, "report_id": report.get("report_id"), "markdown_body": markdown, "report_type": "options_pricing_report"}


def generate_options_scenario_report(input_data: dict[str, Any], *, db_path: str | Path | None = None, persist: bool = False, **scenario_kwargs: Any) -> dict[str, Any]:
    scenario = option_scenario_grid(input_data, **scenario_kwargs)
    source = build_options_source_snapshot("manual", used_for_calculation=True)
    result = build_options_result("scenario", "Options Scenario Report", scenario, source, ["Scenario grid is deterministic and based on supplied inputs."])
    markdown = render_options_report_markdown("Options Scenario Report", result, report_kind="options_scenario_report")
    if not persist:
        return {**result, "markdown_body": markdown, "report_type": "options_scenario_report"}
    report = create_report(report_type="options_scenario_report", title="Options Scenario Report", summary="Local research-only option scenario grid.", source_snapshot=source, data_confidence="user-supplied", attachments=[result], markdown_body=markdown, tags=["goal12a", "options", "scenario"], db_path=db_path)
    return {**result, "report": report, "report_id": report.get("report_id"), "markdown_body": markdown, "report_type": "options_scenario_report"}


def generate_options_iv_report(input_data: dict[str, Any], *, market_price: float | None = None, db_path: str | Path | None = None, persist: bool = False) -> dict[str, Any]:
    iv = implied_volatility(input_data, market_price=market_price)
    source = build_options_source_snapshot("manual", used_for_calculation=True)
    result = build_options_result("iv", "Options Implied Volatility Report", iv, source, ["IV solving returns an explicit error instead of a fabricated value when no solution is bracketed."])
    markdown = render_options_report_markdown("Options Implied Volatility Report", result, report_kind="options_iv_report")
    if not persist:
        return {**result, "markdown_body": markdown, "report_type": "options_iv_report"}
    report = create_report(report_type="options_iv_report", title="Options Implied Volatility Report", summary="Local research-only implied volatility calculation.", source_snapshot=source, data_confidence="user-supplied", attachments=[result], markdown_body=markdown, tags=["goal12a", "options", "iv"], db_path=db_path)
    return {**result, "report": report, "report_id": report.get("report_id"), "markdown_body": markdown, "report_type": "options_iv_report"}


def generate_options_payoff_report(payoff_payload: dict[str, Any], *, db_path: str | Path | None = None, persist: bool = False) -> dict[str, Any]:
    source = build_options_source_snapshot("manual", used_for_calculation=True)
    result = build_options_result("payoff", "Options Payoff Report", payoff_payload, source, ["Payoff templates are mathematical profiles only."])
    markdown = render_options_report_markdown("Options Payoff Report", result, report_kind="options_payoff_report")
    if not persist:
        return {**result, "markdown_body": markdown, "report_type": "options_payoff_report"}
    report = create_report(report_type="options_payoff_report", title="Options Payoff Report", summary="Local research-only option payoff profile.", source_snapshot=source, data_confidence="user-supplied", attachments=[result], markdown_body=markdown, tags=["goal12a", "options", "payoff"], db_path=db_path)
    return {**result, "report": report, "report_id": report.get("report_id"), "markdown_body": markdown, "report_type": "options_payoff_report"}
