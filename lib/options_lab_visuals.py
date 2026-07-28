from __future__ import annotations

from typing import Any


def build_options_price_card(pricing_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "Option price",
        "value": pricing_result.get("price"),
        "subtitle": pricing_result.get("model_label", pricing_result.get("model")),
        "contract_value": pricing_result.get("contract_value"),
        "research_only": True,
    }


def build_greeks_table(greeks_result: dict[str, Any]) -> list[dict[str, Any]]:
    greeks = greeks_result.get("greeks", {})
    return [{"greek": key, "value": value, "unit": greeks_result.get("units", {}).get(key, "model units"), "research_only": True} for key, value in greeks.items()]


def build_payoff_chart_payload(payoff_result: dict[str, Any]) -> dict[str, Any]:
    rows = payoff_result.get("rows") or payoff_result.get("table", [])
    return {"x": [row.get("underlying_price_at_expiry") for row in rows], "y": [row.get("total_pnl") for row in rows], "breakeven_points": payoff_result.get("breakeven_points", []), "research_only": True}


def build_scenario_table_payload(scenario_result: dict[str, Any], limit: int = 50) -> dict[str, Any]:
    rows = scenario_result.get("rows", [])[:limit]
    return {"rows": rows, "displayed_rows": len(rows), "total_rows": scenario_result.get("scenario_count", len(rows)), "research_only": True}


def build_chain_quality_panel(chain_snapshot):
    return {"title": "Option Chain Quality", "quality": chain_snapshot.get("quality", {}), "source_snapshot": chain_snapshot.get("source_snapshot", {}), "research_only": True}


def build_option_book_risk_panel(book_snapshot):
    return {"title": "Option Book Risk", "totals": book_snapshot.get("totals", {}), "by_underlying": book_snapshot.get("by_underlying", []), "research_only": True}


def build_quant_diagnostics_panel(snapshot):
    return {"title": "Local Quant Diagnostics", "snapshot": snapshot, "caveat": "Supplied data only; no prediction claim.", "research_only": True}
