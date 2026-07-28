from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

ATTACHMENT_TYPES = {
    "option_analysis_snapshot",
    "quant_model_snapshot",
    "external_provider_snapshot",
    "chart_snapshot",
    "report_snapshot",
    "data_quality_snapshot",
    "actionless_simulation_case",
    "model_artifact_governance_record",
    "data_feed_datasheet",
}

@dataclass(frozen=True)
class ResearchAttachment:
    attachment_type: str
    title: str
    payload: dict[str, Any] = field(default_factory=dict)
    source_snapshot: dict[str, Any] = field(default_factory=dict)


def validate_attachment_type(attachment_type: str) -> str:
    if attachment_type not in ATTACHMENT_TYPES:
        raise ValueError(f"Unsupported research attachment type: {attachment_type}")
    return attachment_type


def build_research_attachment(attachment_type: str, title: str, payload: dict[str, Any] | None = None, source_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    return asdict(ResearchAttachment(validate_attachment_type(attachment_type), title, payload or {}, source_snapshot or {}))
