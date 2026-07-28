from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .actionless_simulation_schema import ACTIONLESS_SIMULATION_NOTICE, redact_private_paths, utc_now
from .research_report_sanitizer import escape_report_identifier

DEFAULT_SIMULATION_ROOT = Path("data/private/actionless_simulations")
INDEX_FILENAME = "simulation_case_index.json"


def _root(base_dir: str | Path | None = None) -> Path:
    return Path(base_dir) if base_dir is not None else DEFAULT_SIMULATION_ROOT


def _index_path(base_dir: str | Path | None = None) -> Path:
    return _root(base_dir) / INDEX_FILENAME


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n", encoding="utf-8", newline="\n")


def _safe_text(value: Any, max_length: int = 200) -> str:
    return escape_report_identifier(value, max_length=max_length)


def _safe_list(values: Any, max_length: int = 120) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return [_safe_text(value, max_length) for value in list(values or []) if str(value).strip()]


def _artifact_counts(manifest: dict[str, Any]) -> dict[str, int]:
    return {
        "scenario_sets": len(manifest.get("scenario_ids") or []),
        "feed_snapshots": len(manifest.get("feed_snapshot_ids") or []),
        "model_artifacts": len(manifest.get("model_artifact_ids") or []),
        "diagnostics": len(manifest.get("diagnostic_ids") or []),
        "reviews": len(manifest.get("review_ids") or []),
    }


def entry_from_simulation_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": _safe_text(manifest.get("case_id", ""), 120),
        "title": _safe_text(manifest.get("title", "Action-less Simulation Case"), 200),
        "objective": _safe_text(manifest.get("objective", ""), 300),
        "status": _safe_text(manifest.get("status", "draft"), 80),
        "created_at": _safe_text(manifest.get("created_at", ""), 80),
        "updated_at": _safe_text(manifest.get("updated_at", utc_now()), 80),
        "linked_options_case_ids": _safe_list(manifest.get("linked_options_case_ids")),
        "linked_strategy_commit_ids": _safe_list(manifest.get("linked_strategy_commit_ids")),
        "scenario_ids": _safe_list(manifest.get("scenario_ids")),
        "feed_snapshot_ids": _safe_list(manifest.get("feed_snapshot_ids")),
        "model_artifact_ids": _safe_list(manifest.get("model_artifact_ids")),
        "diagnostic_ids": _safe_list(manifest.get("diagnostic_ids")),
        "review_ids": _safe_list(manifest.get("review_ids")),
        "artifact_counts": _artifact_counts(manifest),
        "private_storage": True,
        "actionless": True,
        "research_only": True,
    }


def rebuild_simulation_case_index(*, base_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(base_dir)
    entries: list[dict[str, Any]] = []
    if root.exists():
        for manifest_path in sorted(root.glob("*/case_manifest.json")):
            manifest = _read_json(manifest_path, {})
            if manifest.get("case_id"):
                entries.append(entry_from_simulation_manifest(manifest))
    payload = {
        "version": 1,
        "updated_at": utc_now(),
        "case_count": len(entries),
        "entries": sorted(entries, key=lambda row: str(row.get("updated_at", "")), reverse=True),
        "private_storage": True,
        "actionless": True,
        "research_only": True,
        "notice": ACTIONLESS_SIMULATION_NOTICE,
    }
    _write_json(_index_path(base_dir), payload)
    return payload


def load_simulation_case_index(*, base_dir: str | Path | None = None, rebuild_if_missing: bool = True) -> dict[str, Any]:
    path = _index_path(base_dir)
    if not path.exists() and rebuild_if_missing:
        return rebuild_simulation_case_index(base_dir=base_dir)
    return _read_json(
        path,
        {
            "version": 1,
            "case_count": 0,
            "entries": [],
            "private_storage": True,
            "actionless": True,
            "research_only": True,
            "notice": ACTIONLESS_SIMULATION_NOTICE,
        },
    )


def update_simulation_case_index_entry(manifest_or_entry: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    index = load_simulation_case_index(base_dir=base_dir, rebuild_if_missing=False)
    entry = entry_from_simulation_manifest(manifest_or_entry) if "timeline" in manifest_or_entry else dict(manifest_or_entry)
    entry["private_storage"] = True
    entry["actionless"] = True
    entry["research_only"] = True
    entries = [row for row in index.get("entries", []) if row.get("case_id") != entry.get("case_id")]
    entries.append(redact_private_paths(entry))
    index.update(
        {
            "updated_at": utc_now(),
            "case_count": len(entries),
            "entries": sorted(entries, key=lambda row: str(row.get("updated_at", "")), reverse=True),
            "private_storage": True,
            "actionless": True,
            "research_only": True,
            "notice": ACTIONLESS_SIMULATION_NOTICE,
        }
    )
    _write_json(_index_path(base_dir), index)
    return entry


def search_simulation_cases(query: str = "", *, base_dir: str | Path | None = None, limit: int = 25) -> list[dict[str, Any]]:
    q = str(query or "").lower().strip()
    entries = load_simulation_case_index(base_dir=base_dir).get("entries", [])
    if q:
        entries = [
            row
            for row in entries
            if q
            in " ".join(
                [
                    str(row.get("case_id", "")),
                    str(row.get("title", "")),
                    str(row.get("objective", "")),
                    str(row.get("status", "")),
                    " ".join(row.get("linked_options_case_ids", []) or []),
                    " ".join(row.get("linked_strategy_commit_ids", []) or []),
                    " ".join(row.get("model_artifact_ids", []) or []),
                ]
            ).lower()
        ]
    return entries[: int(limit)]


def build_simulation_case_index_summary(*, base_dir: str | Path | None = None) -> dict[str, Any]:
    index = load_simulation_case_index(base_dir=base_dir)
    entries = index.get("entries", [])
    by_status: dict[str, int] = {}
    for row in entries:
        status = str(row.get("status", "unknown"))
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "ok": True,
        "case_count": len(entries),
        "by_status": by_status,
        "private_storage": True,
        "actionless": True,
        "research_only": True,
        "notice": ACTIONLESS_SIMULATION_NOTICE,
    }


def export_simulation_case_index_redacted(*, base_dir: str | Path | None = None) -> dict[str, Any]:
    index = load_simulation_case_index(base_dir=base_dir)
    safe_entries = []
    for row in index.get("entries", []):
        safe_entries.append({key: value for key, value in row.items() if key not in {"case_dir", "absolute_path", "local_path", "private_path"}})
    return {
        "version": index.get("version", 1),
        "case_count": len(safe_entries),
        "entries": redact_private_paths(safe_entries),
        "export_redacted": True,
        "private_paths_redacted": True,
        "private_storage": True,
        "actionless": True,
        "research_only": True,
        "notice": ACTIONLESS_SIMULATION_NOTICE,
    }
