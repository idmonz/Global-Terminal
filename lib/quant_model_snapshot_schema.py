from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE

MODEL_CATEGORIES = {
    "correlation_structure",
    "volatility_model",
    "regime_model",
    "mean_reversion_model",
    "cointegration_model",
    "factor_model",
    "option_model",
    "foundation_model_placeholder",
    "rl_simulation_placeholder",
}


@dataclass(frozen=True)
class QuantModelSnapshot:
    model_id: str
    model_name: str
    category: str
    inputs: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)
    source_references: list[str] = field(default_factory=list)
    artifact_uri: str = ""
    research_only: bool = True
    notice: str = RESEARCH_ONLY_OPTIONS_NOTICE


def validate_model_category(category: str) -> str:
    value = str(category or "option_model")
    if value not in MODEL_CATEGORIES:
        raise ValueError(f"Unsupported model category: {category}")
    return value


def build_model_snapshot(model_id: str, model_name: str, category: str, *, inputs: dict[str, Any] | None = None, diagnostics: dict[str, Any] | None = None, caveats: list[str] | None = None, source_references: list[str] | None = None, artifact_uri: str = "") -> dict[str, Any]:
    return asdict(QuantModelSnapshot(model_id=model_id, model_name=model_name, category=validate_model_category(category), inputs=inputs or {}, diagnostics=diagnostics or {}, caveats=caveats or ["Snapshot is a local research artifact, not a deployed model runtime."], source_references=source_references or [], artifact_uri=artifact_uri))
