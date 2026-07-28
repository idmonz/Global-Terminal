from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .research_report_sanitizer import escape_report_identifier
from .options_research_case_schema import OPTIONS_CASE_NOTICE

DEFAULT_CASE_ROOT = Path("data/private/options_cases")
INDEX_FILENAME = "case_index.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root(base_dir: str | Path | None = None) -> Path:
    return Path(base_dir) if base_dir is not None else DEFAULT_CASE_ROOT


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
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _safe_text(value: Any, max_length: int = 200) -> str:
    return escape_report_identifier(value, max_length=max_length)


def _sanitize_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return [_safe_text(v, 80) for v in list(values or []) if str(v).strip()]


def _artifact_counts(manifest: dict[str, Any]) -> dict[str, int]:
    artifacts = manifest.get("artifacts") or {}
    return {"total": len(artifacts), **{str(key): 1 for key in artifacts}}


def _entry_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    metadata = manifest.get("metadata") or {}
    linked_reports = manifest.get("linked_reports", metadata.get("linked_reports", []))
    linked_commits = manifest.get("linked_strategy_commits", metadata.get("linked_strategy_commits", []))
    surface_quality = manifest.get("surface_quality_score", metadata.get("surface_quality_score"))
    return {
        "case_id": _safe_text(manifest.get("case_id", ""), 120),
        "title": _safe_text(manifest.get("title", "Options Research Case"), 200),
        "underlying": _safe_text(manifest.get("underlying", metadata.get("underlying", "")), 80),
        "source": _safe_text(metadata.get("source") or manifest.get("source", "local_private_options_case_store"), 120),
        "snapshot_time": _safe_text(manifest.get("snapshot_time", metadata.get("snapshot_time", "")), 80),
        "created_at": _safe_text(manifest.get("created_at", ""), 80),
        "updated_at": _safe_text(manifest.get("updated_at", _now()), 80),
        "status": _safe_text(manifest.get("status", "active"), 60),
        "tags": _sanitize_list(manifest.get("tags", metadata.get("tags", []))),
        "surface_quality_score": surface_quality,
        "review_status": _safe_text(manifest.get("review_status", metadata.get("review_status", "new")), 60),
        "linked_reports": _sanitize_list(linked_reports),
        "linked_strategy_commits": _sanitize_list(linked_commits),
        "artifact_counts": _artifact_counts(manifest),
        "private_storage": True,
        "research_only": True,
    }


def rebuild_options_case_index(*, base_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(base_dir)
    entries: list[dict[str, Any]] = []
    if root.exists():
        for manifest_path in sorted(root.glob("*/case_manifest.json")):
            manifest = _read_json(manifest_path, {})
            if manifest.get("case_id"):
                entries.append(_entry_from_manifest(manifest))
    payload = {
        "version": 1,
        "updated_at": _now(),
        "case_count": len(entries),
        "entries": sorted(entries, key=lambda row: str(row.get("updated_at", "")), reverse=True),
        "private_storage": True,
        "research_only": True,
        "notice": OPTIONS_CASE_NOTICE,
    }
    _write_json(_index_path(base_dir), payload)
    return payload


def load_options_case_index(*, base_dir: str | Path | None = None, rebuild_if_missing: bool = True) -> dict[str, Any]:
    path = _index_path(base_dir)
    if not path.exists() and rebuild_if_missing:
        return rebuild_options_case_index(base_dir=base_dir)
    return _read_json(path, {"version": 1, "case_count": 0, "entries": [], "private_storage": True, "research_only": True})


def update_options_case_index_entry(manifest_or_entry: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    index = load_options_case_index(base_dir=base_dir, rebuild_if_missing=False)
    entry = _entry_from_manifest(manifest_or_entry) if "artifacts" in manifest_or_entry or "timeline" in manifest_or_entry else dict(manifest_or_entry)
    entry["case_id"] = _safe_text(entry.get("case_id", ""), 120)
    entry["private_storage"] = True
    entry["research_only"] = True
    entries = [row for row in index.get("entries", []) if row.get("case_id") != entry.get("case_id")]
    entries.append(entry)
    index.update({"updated_at": _now(), "case_count": len(entries), "entries": sorted(entries, key=lambda row: str(row.get("updated_at", "")), reverse=True), "private_storage": True, "research_only": True, "notice": OPTIONS_CASE_NOTICE})
    _write_json(_index_path(base_dir), index)
    return entry


def search_options_research_cases(query: str = "", *, base_dir: str | Path | None = None, limit: int = 25) -> list[dict[str, Any]]:
    q = str(query or "").lower().strip()
    entries = load_options_case_index(base_dir=base_dir).get("entries", [])
    if q:
        entries = [row for row in entries if q in " ".join(str(row.get(k, "")) for k in ("case_id", "title", "underlying", "source", "status", "tags")).lower()]
    return entries[: int(limit)]


def filter_options_cases_by_status(status: str, *, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    needle = str(status or "").lower()
    return [row for row in load_options_case_index(base_dir=base_dir).get("entries", []) if str(row.get("status", "")).lower() == needle]


def filter_options_cases_by_underlying(underlying: str, *, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    needle = str(underlying or "").lower()
    return [row for row in load_options_case_index(base_dir=base_dir).get("entries", []) if needle and needle in str(row.get("underlying", "")).lower()]


def filter_options_cases_by_tag(tag: str, *, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    needle = str(tag or "").lower()
    return [row for row in load_options_case_index(base_dir=base_dir).get("entries", []) if needle in [str(t).lower() for t in row.get("tags", [])]]


def build_options_case_index_summary(*, base_dir: str | Path | None = None) -> dict[str, Any]:
    index = load_options_case_index(base_dir=base_dir)
    entries = index.get("entries", [])
    by_status: dict[str, int] = {}
    by_underlying: dict[str, int] = {}
    for row in entries:
        by_status[str(row.get("status", "unknown"))] = by_status.get(str(row.get("status", "unknown")), 0) + 1
        underlying = str(row.get("underlying") or "unspecified")
        by_underlying[underlying] = by_underlying.get(underlying, 0) + 1
    return {"ok": True, "case_count": len(entries), "by_status": by_status, "by_underlying": by_underlying, "private_storage": True, "research_only": True}


def export_options_case_index_redacted(*, base_dir: str | Path | None = None) -> dict[str, Any]:
    index = load_options_case_index(base_dir=base_dir)
    safe_entries = []
    for row in index.get("entries", []):
        safe_entries.append({k: v for k, v in row.items() if k not in {"case_dir", "absolute_path", "local_path", "private_path"}})
    return {"version": index.get("version", 1), "case_count": len(safe_entries), "entries": safe_entries, "export_redacted": True, "private_paths_redacted": True, "private_storage": True, "research_only": True, "notice": OPTIONS_CASE_NOTICE}
