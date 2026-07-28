from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .options_surface_review_queue import VALID_SURFACE_REVIEW_STATUSES, create_surface_review_item, update_surface_review_status
from .options_research_case_schema import OPTIONS_CASE_NOTICE
from .research_report_sanitizer import escape_report_identifier

DEFAULT_REVIEW_ROOT = Path("data/private/options_cases")
REVIEW_QUEUE_FILENAME = "surface_review_queue.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root(base_dir: str | Path | None = None) -> Path:
    return Path(base_dir) if base_dir is not None else DEFAULT_REVIEW_ROOT


def _queue_path(base_dir: str | Path | None = None) -> Path:
    return _root(base_dir) / REVIEW_QUEUE_FILENAME


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


def _clean_item(item: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    out = dict(item or {})
    if not out.get("review_id"):
        out["review_id"] = f"surface_review_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    out["title"] = escape_report_identifier(out.get("title", "Surface QA Review"), max_length=200)
    out["case_id"] = escape_report_identifier(out.get("case_id", ""), max_length=120)
    status = str(out.get("status") or "new")
    if status not in VALID_SURFACE_REVIEW_STATUSES:
        raise ValueError("invalid_surface_review_status")
    out["status"] = status
    out["anomaly_count"] = int(out.get("anomaly_count", len(out.get("anomalies", []))) or 0)
    out["surface_quality_score"] = out.get("surface_quality_score", out.get("quality_score"))
    out.setdefault("created_at", now)
    out["updated_at"] = now
    if out.get("review_notes"):
        out["review_notes"] = escape_report_identifier(out.get("review_notes"), max_length=1000)
    for key in ("linked_report_id", "linked_strategy_commit_id"):
        if out.get(key):
            out[key] = escape_report_identifier(out.get(key), max_length=120)
    out["notice"] = OPTIONS_CASE_NOTICE
    out["research_only"] = True
    return out


def _load_queue(base_dir: str | Path | None = None) -> dict[str, Any]:
    return _read_json(_queue_path(base_dir), {"version": 1, "items": [], "private_storage": True, "research_only": True, "notice": OPTIONS_CASE_NOTICE})


def _save_queue(payload: dict[str, Any], base_dir: str | Path | None = None) -> dict[str, Any]:
    payload.update({"version": 1, "updated_at": _now(), "count": len(payload.get("items", [])), "private_storage": True, "research_only": True, "notice": OPTIONS_CASE_NOTICE})
    _write_json(_queue_path(base_dir), payload)
    return payload


def save_surface_review_item(item_or_surface_qa: dict[str, Any], *, base_dir: str | Path | None = None, case_id: str = "", title: str = "Surface QA Review") -> dict[str, Any]:
    item = dict(item_or_surface_qa or {})
    if "review_id" not in item:
        item = create_surface_review_item(item, case_id=case_id or str(item.get("case_id", "")), title=title or str(item.get("title", "Surface QA Review")))
    clean = _clean_item(item)
    queue = _load_queue(base_dir)
    items = [row for row in queue.get("items", []) if row.get("review_id") != clean.get("review_id")]
    items.append(clean)
    queue["items"] = sorted(items, key=lambda row: str(row.get("updated_at", "")), reverse=True)
    _save_queue(queue, base_dir)
    return {"ok": True, "review_item": clean, "review_id": clean.get("review_id"), "private_storage": True, "research_only": True}


def list_surface_review_items(*, base_dir: str | Path | None = None, include_archived: bool = True) -> list[dict[str, Any]]:
    items = list(_load_queue(base_dir).get("items", []))
    if not include_archived:
        items = [item for item in items if item.get("status") != "archived"]
    return items


def load_surface_review_item(review_id: str, *, base_dir: str | Path | None = None) -> dict[str, Any]:
    for item in list_surface_review_items(base_dir=base_dir):
        if item.get("review_id") == review_id:
            return item
    raise FileNotFoundError("surface_review_item_not_found")


def update_persistent_surface_review_status(review_id: str, status: str, *, notes: str = "", base_dir: str | Path | None = None) -> dict[str, Any]:
    current = load_surface_review_item(review_id, base_dir=base_dir)
    updated = update_surface_review_status(current, status, notes=notes)
    if status == "archived":
        updated["archived_at"] = _now()
    return save_surface_review_item(updated, base_dir=base_dir)


def archive_surface_review_item(review_id: str, *, notes: str = "", base_dir: str | Path | None = None) -> dict[str, Any]:
    return update_persistent_surface_review_status(review_id, "archived", notes=notes, base_dir=base_dir)


def filter_surface_reviews_by_status(status: str, *, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    needle = str(status or "")
    return [item for item in list_surface_review_items(base_dir=base_dir) if item.get("status") == needle]


def build_persistent_surface_review_queue(*, base_dir: str | Path | None = None, include_archived: bool = False) -> dict[str, Any]:
    items = list_surface_review_items(base_dir=base_dir, include_archived=include_archived)
    visible = [item for item in items if include_archived or item.get("status") != "archived"]
    return {"ok": True, "items": visible, "count": len(visible), "requires_review_count": sum(1 for item in visible if item.get("status") == "requires_review"), "private_storage": True, "research_only": True, "notice": OPTIONS_CASE_NOTICE}


def export_surface_review_queue_redacted(*, base_dir: str | Path | None = None) -> dict[str, Any]:
    queue = build_persistent_surface_review_queue(base_dir=base_dir, include_archived=True)
    safe_items = []
    for item in queue.get("items", []):
        safe_items.append({k: v for k, v in item.items() if k not in {"absolute_path", "local_path", "private_path", "case_dir"}})
    return {"items": safe_items, "count": len(safe_items), "export_redacted": True, "private_paths_redacted": True, "private_storage": True, "research_only": True, "notice": OPTIONS_CASE_NOTICE}
