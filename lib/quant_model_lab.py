from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE
from .quant_model_registry import get_quant_model, list_quant_models
from .quant_model_snapshot_schema import build_model_snapshot


def simple_deterministic_diagnostics(values: list[float] | None = None) -> dict[str, Any]:
    series = [float(v) for v in (values or [])]
    if not series:
        return {"ok": True, "count": 0, "mean": None, "volatility_proxy": None, "min": None, "max": None, "caveat": "No series supplied; diagnostics remain empty.", "research_only": True}
    return {"ok": True, "count": len(series), "mean": mean(series), "volatility_proxy": pstdev(series) if len(series) > 1 else 0.0, "min": min(series), "max": max(series), "research_only": True}


def create_quant_model_snapshot(model_id: str = "option_pricing_core", *, values: list[float] | None = None, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    model = get_quant_model(model_id) or {"model_id": model_id, "model_name": model_id.replace("_", " ").title(), "category": "option_model", "status": "ad_hoc"}
    diagnostics = simple_deterministic_diagnostics(values)
    caveats = [
        "Model snapshot is stored for review only; no autonomous action or market connection is created.",
        "Heavy runtimes such as foundation-model inference and reinforcement learning are intentionally excluded in Goal 12A.",
    ]
    refs = []
    if "kronos" in model_id:
        refs.append("Kronos concept mapping: future model artifact metadata only.")
    if "tensortrade" in model_id:
        refs.append("TensorTrade concept mapping: separation between data, scenario, and action-less research output.")
    return build_model_snapshot(model["model_id"], model["model_name"], model["category"], inputs=inputs or {}, diagnostics=diagnostics, caveats=caveats, source_references=refs)


def build_quant_model_lab_payload() -> dict[str, Any]:
    return {"ok": True, "registry": list_quant_models(), "sample_snapshot": create_quant_model_snapshot(), "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
