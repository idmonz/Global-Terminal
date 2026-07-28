from __future__ import annotations

from pathlib import Path
from typing import Any

from .actionless_simulation_schema import ACTIONLESS_SIMULATION_NOTICE, redact_private_paths
from .actionless_simulation_store import build_simulation_case_redacted_summary, export_simulation_case_redacted
from .report_inbox import create_report
from .research_artifact_store import store_research_artifact
from .research_attachment_models import build_research_attachment
from .strategy_decision_log import get_strategy_commit


def build_simulation_case_attachment(bundle: dict[str, Any], *, title: str | None = None) -> dict[str, Any]:
    manifest = (bundle or {}).get("case_manifest", {})
    payload = redact_private_paths(bundle or {})
    source = {
        "source": "local_actionless_simulation_store",
        "freshness": "redacted_export",
        "confidence": "user_supplied_or_deterministic",
        "research_only": True,
        "actionless": True,
    }
    return build_research_attachment(
        "actionless_simulation_case",
        title or manifest.get("title", "Action-less Simulation Case"),
        payload,
        source,
    )


def build_model_governance_attachment(card: dict[str, Any], *, title: str | None = None) -> dict[str, Any]:
    payload = redact_private_paths(card or {})
    source = {
        "source": "local_model_artifact_governance",
        "freshness": "metadata_card",
        "confidence": "metadata_only",
        "research_only": True,
        "actionless": True,
    }
    return build_research_attachment(
        "model_artifact_governance_record",
        title or payload.get("model_name", "Model Artifact Governance Record"),
        payload,
        source,
    )


def attach_simulation_case_to_report(
    case_id: str,
    *,
    base_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    bundle = export_simulation_case_redacted(case_id, base_dir=base_dir)
    summary = build_simulation_case_redacted_summary(case_id, base_dir=base_dir)
    attachment = build_simulation_case_attachment(bundle)
    title = f"Action-less Simulation Case: {summary.get('title', case_id)}"
    report = create_report(
        report_type="actionless_simulation_case_report",
        title=title,
        summary="Redacted local simulation case bundle attached for research-only review.",
        source_snapshot=attachment.get("source_snapshot", {}),
        data_confidence="user-supplied-or-deterministic",
        provider_gaps=summary.get("caveats", []),
        attachments=[attachment],
        markdown_body=(
            f"# {title}\n\n"
            "This report contains a redacted action-less simulation case summary.\n\n"
            f"{ACTIONLESS_SIMULATION_NOTICE}\n"
        ),
        tags=["goal13a", "actionless_simulation", "model_governance"],
        db_path=db_path,
    )
    return {"ok": True, "case_id": case_id, "report_id": report["report_id"], "report": report, "attachment": attachment, "summary": summary, "actionless": True, "research_only": True}


def attach_simulation_case_to_strategy_commit(
    case_id: str,
    commit_id: str,
    *,
    base_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    commit = get_strategy_commit(commit_id, db_path=db_path)
    if not commit:
        return {"ok": False, "error": "strategy_commit_not_found", "commit_id": commit_id, "case_id": case_id, "actionless": True, "research_only": True}
    bundle = export_simulation_case_redacted(case_id, base_dir=base_dir)
    attachment = build_simulation_case_attachment(bundle)
    artifact = store_research_artifact(
        commit_id,
        "actionless_simulation_case",
        attachment.get("title", "Action-less Simulation Case"),
        payload=attachment,
        db_path=db_path,
    )
    return {"ok": True, "case_id": case_id, "commit_id": commit_id, "artifact": artifact, "attachment": attachment, "actionless": True, "research_only": True}


def attach_model_artifact_card_to_report(card: dict[str, Any], *, db_path: str | Path | None = None) -> dict[str, Any]:
    attachment = build_model_governance_attachment(card)
    report = create_report(
        report_type="model_artifact_governance_report",
        title=attachment.get("title", "Model Artifact Governance Record"),
        summary="Metadata-only model governance card attached for research review.",
        source_snapshot=attachment.get("source_snapshot", {}),
        data_confidence="metadata-only",
        provider_gaps=(card or {}).get("caveats", []),
        attachments=[attachment],
        markdown_body=f"# {attachment.get('title', 'Model Artifact Governance Record')}\n\n{ACTIONLESS_SIMULATION_NOTICE}\n",
        tags=["goal13a", "model_governance", "metadata_only"],
        db_path=db_path,
    )
    return {"ok": True, "report_id": report["report_id"], "report": report, "attachment": attachment, "actionless": True, "research_only": True}


def attach_model_artifact_card_to_strategy_commit(
    commit_id: str,
    card: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    commit = get_strategy_commit(commit_id, db_path=db_path)
    if not commit:
        return {"ok": False, "error": "strategy_commit_not_found", "commit_id": commit_id, "actionless": True, "research_only": True}
    attachment = build_model_governance_attachment(card)
    artifact = store_research_artifact(
        commit_id,
        "model_artifact_governance_record",
        attachment.get("title", "Model Artifact Governance Record"),
        payload=attachment,
        db_path=db_path,
    )
    return {"ok": True, "commit_id": commit_id, "artifact": artifact, "attachment": attachment, "actionless": True, "research_only": True}
