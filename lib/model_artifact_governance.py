from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .actionless_simulation_schema import (
    ACTIONLESS_SIMULATION_NOTICE,
    SIMULATION_REVIEW_STATUSES,
    redact_private_paths,
    sanitize_actionless_list,
    utc_now,
    validate_actionless_text,
    validate_no_private_or_model_path,
    validate_safe_id,
    validate_status,
)
from .quant_model_snapshot_schema import MODEL_CATEGORIES

MODEL_ARTIFACT_LIFECYCLE_STATUSES = {
    "proposed",
    "experimental",
    "review_required",
    "approved_for_research",
    "deprecated",
    "archived",
}

MODEL_ARTIFACT_OUTPUT_TYPES = {
    "diagnostic",
    "scenario_summary",
    "metadata_card",
    "governance_record",
    "result_summary",
    "datasheet_reference",
}

MODEL_GOVERNANCE_CATEGORIES = set(MODEL_CATEGORIES) | {
    "simulation_case_governance",
    "data_feed_governance",
    "external_reference_placeholder",
}

DEFAULT_PROHIBITED_USE = (
    "Prohibited use: not for broker execution, order routing, buy/sell direction, "
    "portfolio rebalancing, hedging instructions, live deployment, autonomous action, "
    "or external model inference."
)


@dataclass(frozen=True)
class ModelArtifactCard:
    model_artifact_id: str
    model_name: str
    category: str
    version: str
    lifecycle_status: str
    intended_use: str
    prohibited_use: str = DEFAULT_PROHIBITED_USE
    input_assumptions: dict[str, Any] = field(default_factory=dict)
    output_type: str = "metadata_card"
    evaluation_summary: str = ""
    caveats: list[str] = field(default_factory=list)
    source_references: list[str] = field(default_factory=list)
    artifact_uri: str = ""
    lineage: dict[str, Any] = field(default_factory=dict)
    owner: str = ""
    reviewer: str = ""
    review_status: str = "new"
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    metadata_only: bool = True
    no_runtime: bool = True
    actionless: bool = True
    research_only: bool = True
    notice: str = ACTIONLESS_SIMULATION_NOTICE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_model_artifact_category(category: str) -> str:
    value = str(category or "external_reference_placeholder").strip()
    if value not in MODEL_GOVERNANCE_CATEGORIES:
        raise ValueError(f"invalid_model_artifact_category:{category}")
    return value


def validate_model_output_type(output_type: str) -> str:
    value = str(output_type or "metadata_card").strip()
    if value not in MODEL_ARTIFACT_OUTPUT_TYPES:
        raise ValueError(f"invalid_model_artifact_output_type:{output_type}")
    return value


def build_model_artifact_card(
    *,
    model_artifact_id: str,
    model_name: str,
    category: str = "external_reference_placeholder",
    version: str = "v1",
    lifecycle_status: str = "review_required",
    intended_use: str = "Local research-only model governance metadata.",
    prohibited_use: str = DEFAULT_PROHIBITED_USE,
    input_assumptions: dict[str, Any] | None = None,
    output_type: str = "metadata_card",
    evaluation_summary: str = "No external inference was run for this governance record.",
    caveats: list[str] | None = None,
    source_references: list[str] | None = None,
    artifact_uri: str = "",
    lineage: dict[str, Any] | None = None,
    owner: str = "",
    reviewer: str = "",
    review_status: str = "new",
    tags: list[str] | None = None,
    aliases: list[str] | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    return ModelArtifactCard(
        model_artifact_id=validate_safe_id(model_artifact_id, field_name="model_artifact_id"),
        model_name=validate_actionless_text(model_name or "Model Artifact", field_name="model_name", max_length=200),
        category=validate_model_artifact_category(category),
        version=validate_actionless_text(version or "v1", field_name="model_version", max_length=80),
        lifecycle_status=validate_status(lifecycle_status, MODEL_ARTIFACT_LIFECYCLE_STATUSES, field_name="model_lifecycle_status"),
        intended_use=validate_actionless_text(intended_use, field_name="model_intended_use", allow_governance_safety=True, max_length=500),
        prohibited_use=validate_actionless_text(prohibited_use, field_name="model_prohibited_use", allow_governance_safety=True, max_length=700),
        input_assumptions=redact_private_paths(input_assumptions or {}),
        output_type=validate_model_output_type(output_type),
        evaluation_summary=validate_actionless_text(evaluation_summary, field_name="evaluation_summary", allow_governance_safety=True, max_length=800),
        caveats=sanitize_actionless_list(caveats, field_name="model_caveat", allow_governance_safety=True)
        or ["metadata_only", "no_external_inference", "no_model_weights_or_checkpoints"],
        source_references=sanitize_actionless_list(source_references, field_name="source_reference", allow_governance_safety=True),
        artifact_uri=validate_no_private_or_model_path(artifact_uri, field_name="artifact_uri"),
        lineage=redact_private_paths(lineage or {}),
        owner=validate_actionless_text(owner, field_name="model_owner", max_length=120),
        reviewer=validate_actionless_text(reviewer, field_name="model_reviewer", max_length=120),
        review_status=validate_status(review_status, SIMULATION_REVIEW_STATUSES, field_name="model_review_status"),
        tags=sanitize_actionless_list(tags, field_name="model_tag", allow_governance_safety=True),
        aliases=sanitize_actionless_list(aliases, field_name="model_alias", allow_governance_safety=True),
        created_at=created_at or utc_now(),
        updated_at=updated_at or utc_now(),
    ).to_dict()


def build_external_model_placeholder_cards() -> list[dict[str, Any]]:
    return [
        build_model_artifact_card(
            model_artifact_id="kronos_metadata_placeholder",
            model_name="Kronos Metadata Placeholder",
            category="foundation_model_placeholder",
            lifecycle_status="review_required",
            intended_use="Document model-card metadata expectations for a future local research artifact.",
            source_references=["Kronos concept reference; metadata only."],
            artifact_uri="metadata://external-reference/kronos",
            tags=["metadata_only", "foundation_model_placeholder"],
            aliases=["kronos_placeholder"],
        ),
        build_model_artifact_card(
            model_artifact_id="tensortrade_actionless_placeholder",
            model_name="TensorTrade Action-less Simulation Placeholder",
            category="rl_simulation_placeholder",
            lifecycle_status="review_required",
            intended_use="Document feed, scenario, and observer separation for local action-less simulation cases.",
            source_references=["TensorTrade concept reference; action execution removed."],
            artifact_uri="metadata://external-reference/tensortrade",
            tags=["metadata_only", "actionless_simulation"],
            aliases=["tensortrade_placeholder"],
        ),
        build_model_artifact_card(
            model_artifact_id="quantdinger_review_placeholder",
            model_name="QuantDinger Review Governance Placeholder",
            category="external_reference_placeholder",
            lifecycle_status="review_required",
            intended_use="Document review-state and lifecycle guardrail concepts for local governance records.",
            source_references=["QuantDinger concept reference; broker/API runtime removed."],
            artifact_uri="metadata://external-reference/quantdinger",
            tags=["metadata_only", "review_governance"],
            aliases=["quantdinger_placeholder"],
        ),
    ]


def build_model_artifact_registry_summary(cards: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = cards if cards is not None else build_external_model_placeholder_cards()
    by_lifecycle: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for row in rows:
        lifecycle = str(row.get("lifecycle_status", "unknown"))
        category = str(row.get("category", "unknown"))
        by_lifecycle[lifecycle] = by_lifecycle.get(lifecycle, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
    return {
        "ok": True,
        "model_artifact_count": len(rows),
        "by_lifecycle": by_lifecycle,
        "by_category": by_category,
        "metadata_only": True,
        "no_runtime": True,
        "actionless": True,
        "research_only": True,
        "notice": ACTIONLESS_SIMULATION_NOTICE,
    }
