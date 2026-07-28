from __future__ import annotations

from typing import Any

from .options_report_generator import generate_options_iv_report, generate_options_payoff_report, generate_options_pricing_report, generate_options_scenario_report


def build_options_lab_report_payload(input_data: dict[str, Any]) -> dict[str, Any]:
    pricing = generate_options_pricing_report(input_data, persist=False)
    scenario = generate_options_scenario_report(input_data, persist=False)
    iv = generate_options_iv_report({**input_data, "premium": pricing.get("payload", {}).get("price") or pricing.get("price")}, persist=False)
    return {"pricing_report": pricing, "scenario_report": scenario, "iv_report": iv, "research_only": True}


def build_local_report_export_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {"filename": "options_research_report.md", "markdown_body": report.get("markdown_body", ""), "local_only": True, "research_only": True}
