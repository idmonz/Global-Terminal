from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .research_report_sanitizer import escape_report_identifier

ACTIONLESS_SIMULATION_NOTICE = (
    "Action-less simulation cases are local research-only artifacts. "
    "They are not investment advice, trading recommendations, trade approvals, "
    "hedging instructions, position-sizing instructions, or execution instructions."
)

SIMULATION_CASE_STATUSES = {"draft", "active", "under_review", "reviewed", "archived"}
SIMULATION_REVIEW_STATUSES = {"new", "queued", "under_review", "needs_revision", "reviewed", "archived"}
SIMULATION_RESULT_STATUSES = {"draft", "generated", "under_review", "reviewed", "archived"}

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
_ABSOLUTE_PATH_RE = re.compile(r"(?i)(?:(?<![A-Za-z0-9])[A-Z]:[\\/]|/(?:home|users|mnt|tmp|private|secret|var)/|data/private/)")
_MODEL_FILE_SUFFIXES = (".ckpt", ".h5", ".joblib", ".onnx", ".pt", ".pth", ".safetensors")

_FORBIDDEN_ACTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\btrade\s+now\b", "trade_now"),
    (r"\bexecute(?:s|d|ing)?\b", "execute"),
    (r"\bexecution\b", "execution"),
    (r"\border(?:s|ed|ing)?\b", "order"),
    (r"\bbroker\b", "broker"),
    (r"\bbuy\b", "buy"),
    (r"\bsell\b", "sell"),
    (r"\brebalance(?:s|d|ing)?\b", "rebalance"),
    (r"\bdeploy\s+strategy\b", "deploy_strategy"),
    (r"\bposition[-\s]?sizing\b", "position_sizing"),
    (r"\bhedg(?:e|ing)\s+instruction", "hedging_instruction"),
    (r"\btrade\s+recommendation", "trade_recommendation"),
)

_GOVERNANCE_SAFETY_REPLACEMENTS = (
    r"not investment advice",
    r"not a trading recommendation",
    r"not trading recommendations",
    r"trading recommendations",
    r"not trade approvals",
    r"trade approvals",
    r"not execution instructions",
    r"not an execution instruction",
    r"execution instructions",
    r"not broker execution",
    r"no broker execution",
    r"broker execution",
    r"action execution removed",
    r"execution removed",
    r"broker/api runtime removed",
    r"broker runtime removed",
    r"no order routing",
    r"order routing",
    r"no trading action",
    r"no trade action",
    r"without enabling any trading action",
    r"do not buy or sell",
    r"must not buy or sell",
    r"no buy or sell",
    r"buy/sell",
    r"position-sizing instructions",
    r"position sizing instructions",
    r"hedging instructions",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_safe_id(value: Any, *, field_name: str = "id") -> str:
    text = str(value or "").strip()
    if not text or text in {".", ".."}:
        raise ValueError(f"invalid_{field_name}")
    if "/" in text or "\\" in text or ".." in text:
        raise ValueError(f"invalid_{field_name}_path_traversal")
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"invalid_{field_name}")
    return text


def validate_safe_id_list(values: Any, *, field_name: str) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return [validate_safe_id(value, field_name=field_name) for value in list(values or []) if str(value).strip()]


def validate_status(value: Any, allowed: set[str], *, field_name: str) -> str:
    status = str(value or "").strip() or next(iter(sorted(allowed)))
    if status not in allowed:
        raise ValueError(f"invalid_{field_name}")
    return status


def _strip_governance_safety_language(text: str) -> str:
    lowered = text.lower()
    for phrase in _GOVERNANCE_SAFETY_REPLACEMENTS:
        lowered = re.sub(re.escape(phrase), " ", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\b(?:prohibited|forbidden)\s+use\s*:\s*", " ", lowered)
    lowered = re.sub(r"\bnot\s+for\s+[^.;]+", " ", lowered)
    lowered = re.sub(r"\b(?:do not|must not|never|no)\s+use\s+(?:for|to)\s+", " ", lowered)
    return lowered


def validate_actionless_text(
    value: Any,
    *,
    field_name: str = "text",
    allow_governance_safety: bool = False,
    max_length: int = 500,
) -> str:
    text = "" if value is None else str(value)
    candidate = _strip_governance_safety_language(text) if allow_governance_safety else text.lower()
    for pattern, label in _FORBIDDEN_ACTION_PATTERNS:
        if re.search(pattern, candidate, flags=re.IGNORECASE):
            raise ValueError(f"action_language_blocked:{field_name}:{label}")
    return escape_report_identifier(text, max_length=max_length)


def sanitize_actionless_list(values: Any, *, field_name: str, allow_governance_safety: bool = False) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return [
        validate_actionless_text(value, field_name=field_name, allow_governance_safety=allow_governance_safety, max_length=300)
        for value in list(values or [])
        if str(value).strip()
    ]


def validate_no_private_or_model_path(value: Any, *, field_name: str = "path") -> str:
    text = "" if value is None else str(value).strip()
    lowered = text.lower()
    if text and (_ABSOLUTE_PATH_RE.search(text) or any(lowered.endswith(suffix) for suffix in _MODEL_FILE_SUFFIXES)):
        raise ValueError(f"unsafe_{field_name}")
    return escape_report_identifier(text, max_length=300)


def redact_private_paths(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if str(key) in {"case_dir", "absolute_path", "local_path", "private_path", "path_on_disk"}:
                out[str(key)] = "[local-path-redacted]"
            else:
                out[str(key)] = redact_private_paths(item)
        return out
    if isinstance(value, list):
        return [redact_private_paths(item) for item in value]
    if isinstance(value, str):
        text = _ABSOLUTE_PATH_RE.sub("[local-path-redacted]", value)
        return escape_report_identifier(text, max_length=800)
    return value


def validate_actionless_mapping(payload: dict[str, Any] | None, *, field_name: str = "payload") -> dict[str, Any]:
    clean = redact_private_paths(payload or {})
    for key, value in clean.items():
        if isinstance(value, str):
            clean[key] = validate_actionless_text(
                value,
                field_name=f"{field_name}.{key}",
                allow_governance_safety=str(key) in {"notice", "caveat", "caveats", "prohibited_use"},
                max_length=800,
            )
        elif isinstance(value, dict):
            clean[key] = validate_actionless_mapping(value, field_name=f"{field_name}.{key}")
        elif isinstance(value, list):
            clean[key] = [validate_actionless_mapping({"value": item}, field_name=f"{field_name}.{key}").get("value") if isinstance(item, str) else redact_private_paths(item) for item in value]
    return clean


@dataclass(frozen=True)
class ActionlessSimulationCaseManifest:
    case_id: str
    title: str
    objective: str
    created_at: str
    updated_at: str
    status: str = "draft"
    source_context: dict[str, Any] = field(default_factory=dict)
    linked_options_case_ids: list[str] = field(default_factory=list)
    linked_strategy_commit_ids: list[str] = field(default_factory=list)
    scenario_ids: list[str] = field(default_factory=list)
    feed_snapshot_ids: list[str] = field(default_factory=list)
    model_artifact_ids: list[str] = field(default_factory=list)
    diagnostic_ids: list[str] = field(default_factory=list)
    review_ids: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=lambda: ["local_private_only", "excluded_from_release", "metadata_and_diagnostics_only"])
    notices: list[str] = field(default_factory=lambda: [ACTIONLESS_SIMULATION_NOTICE])
    timeline: list[dict[str, Any]] = field(default_factory=list)
    private_storage: bool = True
    actionless: bool = True
    research_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioSet:
    scenario_id: str
    title: str
    horizon: str
    asset_universe: list[str] = field(default_factory=list)
    macro_assumptions: list[str] = field(default_factory=list)
    geopolitical_assumptions: list[str] = field(default_factory=list)
    volatility_assumptions: list[str] = field(default_factory=list)
    options_surface_refs: list[str] = field(default_factory=list)
    stress_parameters: dict[str, Any] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    actionless: bool = True
    research_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DataFeedSnapshot:
    feed_snapshot_id: str
    data_source_label: str
    generated_at: str
    coverage: dict[str, Any] = field(default_factory=dict)
    fields: list[str] = field(default_factory=list)
    transformations: list[str] = field(default_factory=list)
    freshness: str = "user_supplied_or_local_snapshot"
    limitations: list[str] = field(default_factory=list)
    missingness_notes: list[str] = field(default_factory=list)
    privacy_notes: list[str] = field(default_factory=list)
    intended_research_use: str = "Local research-only diagnostic context."
    source_context: dict[str, Any] = field(default_factory=dict)
    actionless: bool = True
    research_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SimulationResultArtifact:
    result_id: str
    scenario_id: str
    model_artifact_id: str
    input_snapshot_id: str
    metrics: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=utc_now)
    provenance: dict[str, Any] = field(default_factory=dict)
    status: str = "generated"
    notice: str = ACTIONLESS_SIMULATION_NOTICE
    actionless: bool = True
    research_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SimulationReviewItem:
    review_id: str
    case_id: str
    artifact_type: str
    artifact_id: str
    title: str
    status: str = "new"
    reviewer: str = ""
    notes: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    caveats: list[str] = field(default_factory=list)
    actionless: bool = True
    research_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_simulation_case_manifest(
    *,
    case_id: str,
    title: str,
    objective: str,
    created_at: str | None = None,
    updated_at: str | None = None,
    status: str = "draft",
    source_context: dict[str, Any] | None = None,
    linked_options_case_ids: list[str] | None = None,
    linked_strategy_commit_ids: list[str] | None = None,
    scenario_ids: list[str] | None = None,
    feed_snapshot_ids: list[str] | None = None,
    model_artifact_ids: list[str] | None = None,
    diagnostic_ids: list[str] | None = None,
    review_ids: list[str] | None = None,
    caveats: list[str] | None = None,
    notices: list[str] | None = None,
    timeline: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return ActionlessSimulationCaseManifest(
        case_id=validate_safe_id(case_id, field_name="case_id"),
        title=validate_actionless_text(title or "Action-less Simulation Case", field_name="title", max_length=200),
        objective=validate_actionless_text(objective or "Research-only simulation case review.", field_name="objective", max_length=500),
        created_at=created_at or utc_now(),
        updated_at=updated_at or utc_now(),
        status=validate_status(status, SIMULATION_CASE_STATUSES, field_name="case_status"),
        source_context=redact_private_paths(source_context or {}),
        linked_options_case_ids=validate_safe_id_list(linked_options_case_ids, field_name="linked_options_case_id"),
        linked_strategy_commit_ids=validate_safe_id_list(linked_strategy_commit_ids, field_name="linked_strategy_commit_id"),
        scenario_ids=validate_safe_id_list(scenario_ids, field_name="scenario_id"),
        feed_snapshot_ids=validate_safe_id_list(feed_snapshot_ids, field_name="feed_snapshot_id"),
        model_artifact_ids=validate_safe_id_list(model_artifact_ids, field_name="model_artifact_id"),
        diagnostic_ids=validate_safe_id_list(diagnostic_ids, field_name="diagnostic_id"),
        review_ids=validate_safe_id_list(review_ids, field_name="review_id"),
        caveats=sanitize_actionless_list(caveats, field_name="case_caveat", allow_governance_safety=True) or ["local_private_only", "excluded_from_release", "metadata_and_diagnostics_only"],
        notices=sanitize_actionless_list(notices, field_name="case_notice", allow_governance_safety=True) or [ACTIONLESS_SIMULATION_NOTICE],
        timeline=redact_private_paths(timeline or []),
    ).to_dict()


def build_scenario_set(
    *,
    scenario_id: str,
    title: str,
    horizon: str,
    asset_universe: list[str] | None = None,
    macro_assumptions: list[str] | None = None,
    geopolitical_assumptions: list[str] | None = None,
    volatility_assumptions: list[str] | None = None,
    options_surface_refs: list[str] | None = None,
    stress_parameters: dict[str, Any] | None = None,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    return ScenarioSet(
        scenario_id=validate_safe_id(scenario_id, field_name="scenario_id"),
        title=validate_actionless_text(title or "Scenario Set", field_name="scenario_title", max_length=200),
        horizon=validate_actionless_text(horizon or "unspecified", field_name="scenario_horizon", max_length=120),
        asset_universe=sanitize_actionless_list(asset_universe, field_name="asset_universe"),
        macro_assumptions=sanitize_actionless_list(macro_assumptions, field_name="macro_assumption"),
        geopolitical_assumptions=sanitize_actionless_list(geopolitical_assumptions, field_name="geopolitical_assumption"),
        volatility_assumptions=sanitize_actionless_list(volatility_assumptions, field_name="volatility_assumption"),
        options_surface_refs=validate_safe_id_list(options_surface_refs, field_name="options_surface_ref"),
        stress_parameters=redact_private_paths(stress_parameters or {}),
        caveats=sanitize_actionless_list(caveats, field_name="scenario_caveat", allow_governance_safety=True),
    ).to_dict()


def build_data_feed_snapshot(
    *,
    feed_snapshot_id: str,
    data_source_label: str,
    generated_at: str | None = None,
    coverage: dict[str, Any] | None = None,
    fields: list[str] | None = None,
    transformations: list[str] | None = None,
    freshness: str = "user_supplied_or_local_snapshot",
    limitations: list[str] | None = None,
    missingness_notes: list[str] | None = None,
    privacy_notes: list[str] | None = None,
    intended_research_use: str = "Local research-only diagnostic context.",
    source_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return DataFeedSnapshot(
        feed_snapshot_id=validate_safe_id(feed_snapshot_id, field_name="feed_snapshot_id"),
        data_source_label=validate_actionless_text(data_source_label or "local snapshot", field_name="data_source_label", max_length=200),
        generated_at=generated_at or utc_now(),
        coverage=redact_private_paths(coverage or {}),
        fields=sanitize_actionless_list(fields, field_name="data_field"),
        transformations=sanitize_actionless_list(transformations, field_name="transformation"),
        freshness=validate_actionless_text(freshness, field_name="freshness", max_length=120),
        limitations=sanitize_actionless_list(limitations, field_name="limitation", allow_governance_safety=True),
        missingness_notes=sanitize_actionless_list(missingness_notes, field_name="missingness_note", allow_governance_safety=True),
        privacy_notes=sanitize_actionless_list(privacy_notes, field_name="privacy_note", allow_governance_safety=True),
        intended_research_use=validate_actionless_text(intended_research_use, field_name="intended_research_use", allow_governance_safety=True, max_length=400),
        source_context=redact_private_paths(source_context or {}),
    ).to_dict()


def build_simulation_result_artifact(
    *,
    result_id: str,
    scenario_id: str,
    model_artifact_id: str,
    input_snapshot_id: str,
    metrics: dict[str, Any] | None = None,
    diagnostics: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    limitations: list[str] | None = None,
    generated_at: str | None = None,
    provenance: dict[str, Any] | None = None,
    status: str = "generated",
) -> dict[str, Any]:
    return SimulationResultArtifact(
        result_id=validate_safe_id(result_id, field_name="result_id"),
        scenario_id=validate_safe_id(scenario_id, field_name="scenario_id"),
        model_artifact_id=validate_safe_id(model_artifact_id, field_name="model_artifact_id"),
        input_snapshot_id=validate_safe_id(input_snapshot_id, field_name="input_snapshot_id"),
        metrics=redact_private_paths(metrics or {}),
        diagnostics=redact_private_paths(diagnostics or {}),
        warnings=sanitize_actionless_list(warnings, field_name="result_warning", allow_governance_safety=True),
        limitations=sanitize_actionless_list(limitations, field_name="result_limitation", allow_governance_safety=True),
        generated_at=generated_at or utc_now(),
        provenance=redact_private_paths(provenance or {}),
        status=validate_status(status, SIMULATION_RESULT_STATUSES, field_name="result_status"),
    ).to_dict()


def build_simulation_review_item(
    *,
    review_id: str,
    case_id: str,
    artifact_type: str,
    artifact_id: str,
    title: str,
    status: str = "new",
    reviewer: str = "",
    notes: str = "",
    created_at: str | None = None,
    updated_at: str | None = None,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    return SimulationReviewItem(
        review_id=validate_safe_id(review_id, field_name="review_id"),
        case_id=validate_safe_id(case_id, field_name="case_id"),
        artifact_type=validate_safe_id(artifact_type or "simulation_case", field_name="artifact_type"),
        artifact_id=validate_safe_id(artifact_id, field_name="artifact_id"),
        title=validate_actionless_text(title or "Simulation Review Item", field_name="review_title", max_length=200),
        status=validate_status(status, SIMULATION_REVIEW_STATUSES, field_name="review_status"),
        reviewer=validate_actionless_text(reviewer, field_name="reviewer", max_length=120),
        notes=validate_actionless_text(notes, field_name="review_notes", allow_governance_safety=True, max_length=800),
        created_at=created_at or utc_now(),
        updated_at=updated_at or utc_now(),
        caveats=sanitize_actionless_list(caveats, field_name="review_caveat", allow_governance_safety=True),
    ).to_dict()
