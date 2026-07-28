from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .actionless_simulation_schema import (
    ACTIONLESS_SIMULATION_NOTICE,
    build_data_feed_snapshot,
    build_scenario_set,
    build_simulation_case_manifest,
    build_simulation_result_artifact,
    build_simulation_review_item,
    redact_private_paths,
    utc_now,
    validate_actionless_text,
    validate_safe_id,
)
from .model_artifact_governance import DEFAULT_PROHIBITED_USE, build_model_artifact_card

DEFAULT_SIMULATION_ROOT = Path("data/private/actionless_simulations")
_ARTIFACT_DIRS = {
    "scenario_set": "scenario_sets",
    "feed_snapshot": "feed_snapshots",
    "model_artifact": "model_artifacts",
    "simulation_result": "simulation_results",
    "review_item": "reviews",
}


def _generated_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _root(base_dir: str | Path | None = None) -> Path:
    return Path(base_dir) if base_dir is not None else DEFAULT_SIMULATION_ROOT


def _case_dir(case_id: str, base_dir: str | Path | None = None) -> Path:
    root = _root(base_dir).resolve()
    cid = validate_safe_id(case_id, field_name="case_id")
    path = (root / cid).resolve()
    if root not in path.parents and path != root:
        raise ValueError("simulation_case_path_traversal_blocked")
    return path


def _manifest_path(case_id: str, base_dir: str | Path | None = None) -> Path:
    return _case_dir(case_id, base_dir) / "case_manifest.json"


def _artifact_path(case_id: str, artifact_key: str, artifact_id: str, base_dir: str | Path | None = None) -> Path:
    if artifact_key not in _ARTIFACT_DIRS:
        raise ValueError("unsupported_simulation_artifact")
    folder = _case_dir(case_id, base_dir) / _ARTIFACT_DIRS[artifact_key]
    return folder / f"{validate_safe_id(artifact_id, field_name='artifact_id')}.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n", encoding="utf-8", newline="\n")


def _sync_case_index(manifest: dict[str, Any], *, base_dir: str | Path | None = None) -> None:
    try:
        from .actionless_simulation_index import update_simulation_case_index_entry

        update_simulation_case_index_entry(manifest, base_dir=base_dir)
    except Exception:
        pass


def _append_unique(values: list[str], value: str) -> list[str]:
    out = [str(item) for item in values if str(item).strip()]
    if value not in out:
        out.append(value)
    return out


def _load_manifest_required(case_id: str, *, base_dir: str | Path | None = None) -> tuple[Path, dict[str, Any]]:
    path = _manifest_path(case_id, base_dir)
    if not path.exists():
        raise FileNotFoundError("simulation_case_not_found")
    return path, _read_json(path, {})


def _record_timeline(manifest: dict[str, Any], event: str, **extra: Any) -> dict[str, Any]:
    now = utc_now()
    manifest["updated_at"] = now
    manifest.setdefault("timeline", []).append({"event": event, "timestamp": now, "research_only": True, "actionless": True, **redact_private_paths(extra)})
    return manifest


def create_actionless_simulation_case(
    title: str = "Action-less Simulation Case",
    *,
    objective: str = "Research-only simulation case review.",
    case_id: str | None = None,
    base_dir: str | Path | None = None,
    source_context: dict[str, Any] | None = None,
    linked_options_case_ids: list[str] | None = None,
    linked_strategy_commit_ids: list[str] | None = None,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    cid = validate_safe_id(case_id or _generated_id("sim_case"), field_name="case_id")
    now = utc_now()
    folder = _case_dir(cid, base_dir)
    folder.mkdir(parents=True, exist_ok=True)
    for child in _ARTIFACT_DIRS.values():
        (folder / child).mkdir(exist_ok=True)
    manifest = build_simulation_case_manifest(
        case_id=cid,
        title=title,
        objective=objective,
        created_at=now,
        updated_at=now,
        status="draft",
        source_context=source_context,
        linked_options_case_ids=linked_options_case_ids,
        linked_strategy_commit_ids=linked_strategy_commit_ids,
        caveats=caveats,
        timeline=[{"event": "simulation_case_created", "timestamp": now, "research_only": True, "actionless": True}],
    )
    _write_json(folder / "case_manifest.json", manifest)
    _sync_case_index(manifest, base_dir=base_dir)
    return {**manifest, "case_dir": str(folder), "private_storage": True, "actionless": True, "research_only": True}


def load_actionless_simulation_case(case_id: str, *, base_dir: str | Path | None = None) -> dict[str, Any]:
    path, manifest = _load_manifest_required(case_id, base_dir=base_dir)
    return {**manifest, "case_dir": str(path.parent), "private_storage": True, "actionless": True, "research_only": True}


def list_actionless_simulation_cases(*, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    root = _root(base_dir)
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.glob("*/case_manifest.json")):
        try:
            rows.append(_read_json(path, {}))
        except Exception:
            continue
    return sorted(rows, key=lambda row: str(row.get("updated_at", "")), reverse=True)


def update_actionless_simulation_case(
    case_id: str,
    *,
    title: str | None = None,
    objective: str | None = None,
    status: str | None = None,
    source_context: dict[str, Any] | None = None,
    linked_options_case_ids: list[str] | None = None,
    linked_strategy_commit_ids: list[str] | None = None,
    caveats: list[str] | None = None,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    path, manifest = _load_manifest_required(case_id, base_dir=base_dir)
    next_manifest = build_simulation_case_manifest(
        case_id=manifest["case_id"],
        title=title if title is not None else manifest.get("title", "Action-less Simulation Case"),
        objective=objective if objective is not None else manifest.get("objective", "Research-only simulation case review."),
        created_at=manifest.get("created_at") or utc_now(),
        updated_at=utc_now(),
        status=status or manifest.get("status", "draft"),
        source_context=source_context if source_context is not None else manifest.get("source_context", {}),
        linked_options_case_ids=linked_options_case_ids if linked_options_case_ids is not None else manifest.get("linked_options_case_ids", []),
        linked_strategy_commit_ids=linked_strategy_commit_ids if linked_strategy_commit_ids is not None else manifest.get("linked_strategy_commit_ids", []),
        scenario_ids=manifest.get("scenario_ids", []),
        feed_snapshot_ids=manifest.get("feed_snapshot_ids", []),
        model_artifact_ids=manifest.get("model_artifact_ids", []),
        diagnostic_ids=manifest.get("diagnostic_ids", []),
        review_ids=manifest.get("review_ids", []),
        caveats=caveats if caveats is not None else manifest.get("caveats", []),
        notices=manifest.get("notices", [ACTIONLESS_SIMULATION_NOTICE]),
        timeline=manifest.get("timeline", []),
    )
    _record_timeline(next_manifest, "simulation_case_updated", status=next_manifest.get("status"))
    _write_json(path, next_manifest)
    _sync_case_index(next_manifest, base_dir=base_dir)
    return {**next_manifest, "case_dir": str(path.parent), "private_storage": True, "actionless": True, "research_only": True}


def save_scenario_set_to_case(case_id: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    manifest_path, manifest = _load_manifest_required(case_id, base_dir=base_dir)
    data = payload or {}
    scenario_id = validate_safe_id(data.get("scenario_id") or _generated_id("scenario"), field_name="scenario_id")
    scenario = build_scenario_set(
        scenario_id=scenario_id,
        title=data.get("title", "Scenario Set"),
        horizon=data.get("horizon", "unspecified"),
        asset_universe=data.get("asset_universe", []),
        macro_assumptions=data.get("macro_assumptions", []),
        geopolitical_assumptions=data.get("geopolitical_assumptions", []),
        volatility_assumptions=data.get("volatility_assumptions", []),
        options_surface_refs=data.get("options_surface_refs", []),
        stress_parameters=data.get("stress_parameters", {}),
        caveats=data.get("caveats", []),
    )
    path = _artifact_path(case_id, "scenario_set", scenario_id, base_dir)
    _write_json(path, scenario)
    manifest["scenario_ids"] = _append_unique(manifest.get("scenario_ids", []), scenario_id)
    _record_timeline(manifest, "scenario_set_saved", scenario_id=scenario_id, artifact_file=path.name)
    _write_json(manifest_path, manifest)
    _sync_case_index(manifest, base_dir=base_dir)
    return {"ok": True, "case_id": validate_safe_id(case_id, field_name="case_id"), "scenario_id": scenario_id, "scenario_set": scenario, "artifact_file": path.name, "private_storage": True, "actionless": True, "research_only": True, "notice": ACTIONLESS_SIMULATION_NOTICE}


def save_data_feed_snapshot_to_case(case_id: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    manifest_path, manifest = _load_manifest_required(case_id, base_dir=base_dir)
    data = payload or {}
    feed_snapshot_id = validate_safe_id(data.get("feed_snapshot_id") or _generated_id("feed"), field_name="feed_snapshot_id")
    feed = build_data_feed_snapshot(
        feed_snapshot_id=feed_snapshot_id,
        data_source_label=data.get("data_source_label", "local snapshot"),
        generated_at=data.get("generated_at"),
        coverage=data.get("coverage", {}),
        fields=data.get("fields", []),
        transformations=data.get("transformations", []),
        freshness=data.get("freshness", "user_supplied_or_local_snapshot"),
        limitations=data.get("limitations", []),
        missingness_notes=data.get("missingness_notes", []),
        privacy_notes=data.get("privacy_notes", []),
        intended_research_use=data.get("intended_research_use", "Local research-only diagnostic context."),
        source_context=data.get("source_context", {}),
    )
    path = _artifact_path(case_id, "feed_snapshot", feed_snapshot_id, base_dir)
    _write_json(path, feed)
    manifest["feed_snapshot_ids"] = _append_unique(manifest.get("feed_snapshot_ids", []), feed_snapshot_id)
    _record_timeline(manifest, "data_feed_snapshot_saved", feed_snapshot_id=feed_snapshot_id, artifact_file=path.name)
    _write_json(manifest_path, manifest)
    _sync_case_index(manifest, base_dir=base_dir)
    return {"ok": True, "case_id": validate_safe_id(case_id, field_name="case_id"), "feed_snapshot_id": feed_snapshot_id, "feed_snapshot": feed, "artifact_file": path.name, "private_storage": True, "actionless": True, "research_only": True, "notice": ACTIONLESS_SIMULATION_NOTICE}


def save_model_artifact_card_to_case(case_id: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    manifest_path, manifest = _load_manifest_required(case_id, base_dir=base_dir)
    data = payload or {}
    model_artifact_id = validate_safe_id(data.get("model_artifact_id") or _generated_id("model"), field_name="model_artifact_id")
    card = build_model_artifact_card(
        model_artifact_id=model_artifact_id,
        model_name=data.get("model_name", "Model Artifact"),
        category=data.get("category", "external_reference_placeholder"),
        version=data.get("version", "v1"),
        lifecycle_status=data.get("lifecycle_status", "review_required"),
        intended_use=data.get("intended_use", "Local research-only model governance metadata."),
        prohibited_use=data.get("prohibited_use") or DEFAULT_PROHIBITED_USE,
        input_assumptions=data.get("input_assumptions", {}),
        output_type=data.get("output_type", "metadata_card"),
        evaluation_summary=data.get("evaluation_summary", "No external inference was run for this governance record."),
        caveats=data.get("caveats", []),
        source_references=data.get("source_references", []),
        artifact_uri=data.get("artifact_uri", ""),
        lineage=data.get("lineage", {}),
        owner=data.get("owner", ""),
        reviewer=data.get("reviewer", ""),
        review_status=data.get("review_status", "new"),
        tags=data.get("tags", []),
        aliases=data.get("aliases", []),
    )
    path = _artifact_path(case_id, "model_artifact", model_artifact_id, base_dir)
    _write_json(path, card)
    manifest["model_artifact_ids"] = _append_unique(manifest.get("model_artifact_ids", []), model_artifact_id)
    _record_timeline(manifest, "model_artifact_card_saved", model_artifact_id=model_artifact_id, artifact_file=path.name)
    _write_json(manifest_path, manifest)
    _sync_case_index(manifest, base_dir=base_dir)
    return {"ok": True, "case_id": validate_safe_id(case_id, field_name="case_id"), "model_artifact_id": model_artifact_id, "model_artifact_card": card, "artifact_file": path.name, "private_storage": True, "actionless": True, "research_only": True, "notice": ACTIONLESS_SIMULATION_NOTICE}


def save_simulation_result_to_case(case_id: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    manifest_path, manifest = _load_manifest_required(case_id, base_dir=base_dir)
    data = payload or {}
    result_id = validate_safe_id(data.get("result_id") or _generated_id("result"), field_name="result_id")
    result = build_simulation_result_artifact(
        result_id=result_id,
        scenario_id=data.get("scenario_id", "scenario_unspecified"),
        model_artifact_id=data.get("model_artifact_id", "model_artifact_unspecified"),
        input_snapshot_id=data.get("input_snapshot_id", "feed_snapshot_unspecified"),
        metrics=data.get("metrics", {}),
        diagnostics=data.get("diagnostics", {}),
        warnings=data.get("warnings", []),
        limitations=data.get("limitations", []),
        generated_at=data.get("generated_at"),
        provenance=data.get("provenance", {}),
        status=data.get("status", "generated"),
    )
    path = _artifact_path(case_id, "simulation_result", result_id, base_dir)
    _write_json(path, result)
    manifest["diagnostic_ids"] = _append_unique(manifest.get("diagnostic_ids", []), result_id)
    _record_timeline(manifest, "simulation_result_saved", result_id=result_id, artifact_file=path.name)
    _write_json(manifest_path, manifest)
    _sync_case_index(manifest, base_dir=base_dir)
    return {"ok": True, "case_id": validate_safe_id(case_id, field_name="case_id"), "result_id": result_id, "simulation_result": result, "artifact_file": path.name, "private_storage": True, "actionless": True, "research_only": True, "notice": ACTIONLESS_SIMULATION_NOTICE}


def save_simulation_review_item(case_id: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    manifest_path, manifest = _load_manifest_required(case_id, base_dir=base_dir)
    data = payload or {}
    review_id = validate_safe_id(data.get("review_id") or _generated_id("review"), field_name="review_id")
    review = build_simulation_review_item(
        review_id=review_id,
        case_id=case_id,
        artifact_type=data.get("artifact_type", "simulation_case"),
        artifact_id=data.get("artifact_id", case_id),
        title=data.get("title", "Simulation Review Item"),
        status=data.get("status", "new"),
        reviewer=data.get("reviewer", ""),
        notes=data.get("notes", ""),
        caveats=data.get("caveats", []),
    )
    path = _artifact_path(case_id, "review_item", review_id, base_dir)
    _write_json(path, review)
    manifest["review_ids"] = _append_unique(manifest.get("review_ids", []), review_id)
    _record_timeline(manifest, "simulation_review_item_saved", review_id=review_id, artifact_file=path.name)
    _write_json(manifest_path, manifest)
    _sync_case_index(manifest, base_dir=base_dir)
    return {"ok": True, "case_id": validate_safe_id(case_id, field_name="case_id"), "review_id": review_id, "review_item": review, "artifact_file": path.name, "private_storage": True, "actionless": True, "research_only": True, "notice": ACTIONLESS_SIMULATION_NOTICE}


def update_simulation_review_status(
    case_id: str,
    review_id: str,
    status: str,
    *,
    notes: str = "",
    reviewer: str = "",
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    manifest_path, manifest = _load_manifest_required(case_id, base_dir=base_dir)
    path = _artifact_path(case_id, "review_item", review_id, base_dir)
    if not path.exists():
        raise FileNotFoundError("simulation_review_not_found")
    existing = _read_json(path, {})
    review = build_simulation_review_item(
        review_id=review_id,
        case_id=case_id,
        artifact_type=existing.get("artifact_type", "simulation_case"),
        artifact_id=existing.get("artifact_id", case_id),
        title=existing.get("title", "Simulation Review Item"),
        status=status,
        reviewer=reviewer if reviewer else existing.get("reviewer", ""),
        notes=validate_actionless_text(notes if notes else existing.get("notes", ""), field_name="review_notes", allow_governance_safety=True, max_length=800),
        created_at=existing.get("created_at"),
        updated_at=utc_now(),
        caveats=existing.get("caveats", []),
    )
    _write_json(path, review)
    _record_timeline(manifest, "simulation_review_status_updated", review_id=review_id, status=review.get("status"))
    _write_json(manifest_path, manifest)
    _sync_case_index(manifest, base_dir=base_dir)
    return {"ok": True, "case_id": validate_safe_id(case_id, field_name="case_id"), "review_id": validate_safe_id(review_id, field_name="review_id"), "review_item": review, "private_storage": True, "actionless": True, "research_only": True, "notice": ACTIONLESS_SIMULATION_NOTICE}


def _load_artifacts(case_id: str, ids: list[str], artifact_key: str, *, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact_id in ids or []:
        path = _artifact_path(case_id, artifact_key, artifact_id, base_dir)
        if path.exists():
            rows.append(_read_json(path, {}))
    return rows


def export_simulation_case_redacted(case_id: str, *, base_dir: str | Path | None = None) -> dict[str, Any]:
    manifest = load_actionless_simulation_case(case_id, base_dir=base_dir)
    manifest.pop("case_dir", None)
    bundle = {
        "bundle_version": 1,
        "exported_at": utc_now(),
        "case_manifest": manifest,
        "scenario_sets": _load_artifacts(case_id, manifest.get("scenario_ids", []), "scenario_set", base_dir=base_dir),
        "feed_snapshots": _load_artifacts(case_id, manifest.get("feed_snapshot_ids", []), "feed_snapshot", base_dir=base_dir),
        "model_artifact_cards": _load_artifacts(case_id, manifest.get("model_artifact_ids", []), "model_artifact", base_dir=base_dir),
        "simulation_results": _load_artifacts(case_id, manifest.get("diagnostic_ids", []), "simulation_result", base_dir=base_dir),
        "review_items": _load_artifacts(case_id, manifest.get("review_ids", []), "review_item", base_dir=base_dir),
        "export_redacted": True,
        "private_paths_redacted": True,
        "private_storage": True,
        "actionless": True,
        "research_only": True,
        "notice": ACTIONLESS_SIMULATION_NOTICE,
    }
    return redact_private_paths(bundle)


def build_simulation_case_redacted_summary(case_id: str, *, base_dir: str | Path | None = None) -> dict[str, Any]:
    bundle = export_simulation_case_redacted(case_id, base_dir=base_dir)
    manifest = bundle.get("case_manifest", {})
    return {
        "case_id": manifest.get("case_id", ""),
        "title": manifest.get("title", "Action-less Simulation Case"),
        "objective": manifest.get("objective", ""),
        "status": manifest.get("status", "draft"),
        "scenario_count": len(bundle.get("scenario_sets", [])),
        "feed_snapshot_count": len(bundle.get("feed_snapshots", [])),
        "model_artifact_count": len(bundle.get("model_artifact_cards", [])),
        "result_count": len(bundle.get("simulation_results", [])),
        "review_count": len(bundle.get("review_items", [])),
        "export_redacted": True,
        "private_paths_redacted": True,
        "actionless": True,
        "research_only": True,
        "notice": ACTIONLESS_SIMULATION_NOTICE,
    }
