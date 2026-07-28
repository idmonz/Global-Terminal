from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .options_research_case_schema import OPTIONS_CASE_NOTICE, OptionsResearchCaseManifest
from .research_report_sanitizer import escape_report_identifier

DEFAULT_CASE_ROOT = Path("data/private/options_cases")
_ARTIFACT_FILES = {
    "chain_snapshot": "chain_snapshot.json",
    "iv_snapshot": "iv_snapshot.json",
    "surface_snapshot": "surface_snapshot.json",
    "surface_qa": "surface_qa.json",
    "surface_diff": "surface_diff.json",
    "option_book_stress": "option_book_stress.json",
    "quant_diagnostics": "quant_diagnostics.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_case_id(value: str | None = None) -> str:
    raw = str(value or f"case_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}")
    if "/" in raw or "\\" in raw or ".." in raw:
        raise ValueError("invalid_case_id_path_traversal")
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("._-")[:80]
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError("invalid_case_id")
    return cleaned


def _root(base_dir: str | Path | None = None) -> Path:
    return Path(base_dir) if base_dir is not None else DEFAULT_CASE_ROOT


def _case_dir(case_id: str, base_dir: str | Path | None = None) -> Path:
    root = _root(base_dir).resolve()
    cid = _safe_case_id(case_id)
    path = (root / cid).resolve()
    if root not in path.parents and path != root:
        raise ValueError("case_path_traversal_blocked")
    return path


def _manifest_path(case_id: str, base_dir: str | Path | None = None) -> Path:
    return _case_dir(case_id, base_dir) / "case_manifest.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _sync_case_index(manifest: dict[str, Any], *, base_dir: str | Path | None = None) -> None:
    try:
        from .options_research_case_index import update_options_case_index_entry
        update_options_case_index_entry(manifest, base_dir=base_dir)
    except Exception:
        # Case persistence must not fail solely because the derived private index failed.
        pass


def _redact_paths(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in {"absolute_path", "local_path", "private_path"}:
                out[k] = "[local-path-redacted]"
            else:
                out[k] = _redact_paths(v)
        return out
    if isinstance(value, list):
        return [_redact_paths(v) for v in value]
    if isinstance(value, str):
        return escape_report_identifier(value)
    return value


def create_options_research_case(title: str = "Options Research Case", *, case_id: str | None = None, base_dir: str | Path | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    cid = _safe_case_id(case_id)
    now = _utc_now()
    folder = _case_dir(cid, base_dir)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "reports").mkdir(exist_ok=True)
    manifest = OptionsResearchCaseManifest(
        case_id=cid,
        title=escape_report_identifier(title),
        created_at=now,
        updated_at=now,
        timeline=[{"event": "case_created", "timestamp": now, "research_only": True}],
    ).to_dict()
    if metadata:
        manifest["metadata"] = _redact_paths(metadata)
    _write_json(folder / "case_manifest.json", manifest)
    _sync_case_index(manifest, base_dir=base_dir)
    return {**manifest, "case_dir": str(folder), "private_storage": True}


def load_options_research_case(case_id: str, *, base_dir: str | Path | None = None) -> dict[str, Any]:
    path = _manifest_path(case_id, base_dir)
    if not path.exists():
        raise FileNotFoundError("options_case_not_found")
    manifest = _read_json(path, {})
    return {**manifest, "case_dir": str(path.parent), "private_storage": True}


def list_options_research_cases(*, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    root = _root(base_dir)
    if not root.exists():
        return []
    rows = []
    for manifest in sorted(root.glob("*/case_manifest.json")):
        try:
            rows.append(_read_json(manifest, {}))
        except Exception:
            continue
    return sorted(rows, key=lambda row: str(row.get("updated_at", "")), reverse=True)


def _save_artifact(case_id: str, artifact_key: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    if artifact_key not in _ARTIFACT_FILES:
        raise ValueError("unsupported_options_case_artifact")
    folder = _case_dir(case_id, base_dir)
    manifest_path = folder / "case_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("options_case_not_found")
    filename = _ARTIFACT_FILES[artifact_key]
    clean_payload = _redact_paths({**(payload or {}), "research_only": True})
    _write_json(folder / filename, clean_payload)
    manifest = _read_json(manifest_path, {})
    now = _utc_now()
    manifest.setdefault("artifacts", {})[artifact_key] = filename
    manifest.setdefault("timeline", []).append({"event": f"{artifact_key}_saved", "timestamp": now, "artifact": filename, "research_only": True})
    manifest["updated_at"] = now
    _write_json(manifest_path, manifest)
    _sync_case_index(manifest, base_dir=base_dir)
    return {"ok": True, "case_id": case_id, "artifact_key": artifact_key, "artifact_file": filename, "private_storage": True, "notice": OPTIONS_CASE_NOTICE, "research_only": True}


def save_chain_snapshot_to_case(case_id: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    return _save_artifact(case_id, "chain_snapshot", payload, base_dir=base_dir)


def save_surface_snapshot_to_case(case_id: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    return _save_artifact(case_id, "surface_snapshot", payload, base_dir=base_dir)


def save_surface_qa_to_case(case_id: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    return _save_artifact(case_id, "surface_qa", payload, base_dir=base_dir)


def save_option_book_stress_to_case(case_id: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    return _save_artifact(case_id, "option_book_stress", payload, base_dir=base_dir)


def save_quant_diagnostics_to_case(case_id: str, payload: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    return _save_artifact(case_id, "quant_diagnostics", payload, base_dir=base_dir)


def build_case_timeline(case_id: str, *, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    return list(load_options_research_case(case_id, base_dir=base_dir).get("timeline", []))


def export_case_manifest_redacted(case_id: str, *, base_dir: str | Path | None = None) -> dict[str, Any]:
    manifest = load_options_research_case(case_id, base_dir=base_dir)
    manifest.pop("case_dir", None)
    return _redact_paths({**manifest, "export_redacted": True, "private_paths_redacted": True})



def update_options_research_case_status(case_id: str, status: str, *, base_dir: str | Path | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest_path = _manifest_path(case_id, base_dir)
    if not manifest_path.exists():
        raise FileNotFoundError("options_case_not_found")
    safe_status = escape_report_identifier(status, max_length=60) or "active"
    manifest = _read_json(manifest_path, {})
    now = _utc_now()
    manifest["status"] = safe_status
    manifest["updated_at"] = now
    if metadata:
        manifest.setdefault("metadata", {}).update(_redact_paths(metadata))
    manifest.setdefault("timeline", []).append({"event": "case_status_updated", "status": safe_status, "timestamp": now, "research_only": True})
    _write_json(manifest_path, manifest)
    _sync_case_index(manifest, base_dir=base_dir)
    return {**manifest, "case_dir": str(manifest_path.parent), "private_storage": True, "research_only": True}

def delete_options_research_case(case_id: str, *, confirm: bool = False, base_dir: str | Path | None = None) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "confirmation_required", "case_id": _safe_case_id(case_id), "research_only": True}
    folder = _case_dir(case_id, base_dir)
    if not folder.exists():
        return {"ok": False, "error": "options_case_not_found", "research_only": True}
    for child in sorted(folder.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    folder.rmdir()
    return {"ok": True, "case_id": _safe_case_id(case_id), "deleted": True, "research_only": True}
