from __future__ import annotations

from typing import Any

from .quant_model_snapshot_schema import MODEL_CATEGORIES

MODEL_REGISTRY: list[dict[str, Any]] = [
    {"model_id": "option_pricing_core", "model_name": "Options Pricing Core", "category": "option_model", "runtime": "local deterministic formulas", "status": "implemented_goal12a"},
    {"model_id": "correlation_structure_placeholder", "model_name": "Correlation/RMT Roadmap", "category": "correlation_structure", "runtime": "placeholder", "status": "future_goal12b"},
    {"model_id": "volatility_model_placeholder", "model_name": "GARCH/Heston/SABR Roadmap", "category": "volatility_model", "runtime": "placeholder", "status": "future_goal12b"},
    {"model_id": "kronos_placeholder", "model_name": "Foundation Model Snapshot Placeholder", "category": "foundation_model_placeholder", "runtime": "none", "status": "metadata_only"},
    {"model_id": "tensortrade_placeholder", "model_name": "Action-less Simulation Placeholder", "category": "rl_simulation_placeholder", "runtime": "none", "status": "metadata_only"},
    {"model_id": "goal13a_simulation_case_governance", "model_name": "Goal 13A Simulation Case Governance", "category": "regime_model", "runtime": "metadata only", "status": "goal13a_metadata_only"},
    {"model_id": "quantdinger_review_placeholder", "model_name": "Review Governance Placeholder", "category": "regime_model", "runtime": "none", "status": "metadata_only"},
]


def list_quant_models() -> list[dict[str, Any]]:
    return [dict(row, research_only=True) for row in MODEL_REGISTRY]


def get_quant_model(model_id: str) -> dict[str, Any] | None:
    return next((row for row in list_quant_models() if row["model_id"] == model_id), None)


def build_model_registry_payload() -> dict[str, Any]:
    rows = list_quant_models()
    return {"ok": True, "models": rows, "categories": sorted(MODEL_CATEGORIES), "research_only": True}
