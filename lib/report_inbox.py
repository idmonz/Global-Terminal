from __future__ import annotations

from pathlib import Path
from typing import Any

from .report_models import REPORT_CAVEAT, validate_report_type
from .research_workspace_db import execute_query, json_dumps, json_loads, new_id, utc_now


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key, default in [
        ("linked_watchlist_items", []), ("linked_assets", []), ("linked_regions", []), ("linked_events", []),
        ("linked_strategy_commits", []), ("provider_gaps_json", []), ("attachments_json", []), ("tags", []),
    ]:
        out[key] = json_loads(out.get(key), default)
    out["source_snapshot_json"] = json_loads(out.get("source_snapshot_json"), {})
    out["archived"] = bool(out.get("archived"))
    out["report_review_status"] = out.get("report_review_status") or ("archived" if out["archived"] else "unread")
    out["reviewed_at"] = out.get("reviewed_at") or ""
    out["review_notes"] = out.get("review_notes") or ""
    return out


def create_report(
    *, report_type: str, title: str, summary: str = "", linked_watchlist_items: list[str] | None = None,
    linked_assets: list[str] | None = None, linked_regions: list[str] | None = None, linked_events: list[str] | None = None,
    linked_strategy_commits: list[str] | None = None, source_snapshot: dict[str, Any] | None = None,
    data_confidence: str = "unknown", provider_gaps: list[str] | None = None, attachments: list[dict[str, Any]] | None = None,
    markdown_body: str = "", html_body_optional: str = "", tags: list[str] | None = None, db_path: str | Path | None = None,
) -> dict[str, Any]:
    now = utc_now()
    body = markdown_body or f"# {title}\n\n{summary}\n\n> {REPORT_CAVEAT}\n"
    row = {
        "report_id": new_id("report"), "report_type": validate_report_type(report_type), "title": title,
        "summary": summary, "generated_at": now, "linked_watchlist_items": json_dumps(linked_watchlist_items or []),
        "linked_assets": json_dumps(linked_assets or []), "linked_regions": json_dumps(linked_regions or []),
        "linked_events": json_dumps(linked_events or []), "linked_strategy_commits": json_dumps(linked_strategy_commits or []),
        "source_snapshot_json": json_dumps(source_snapshot or {"freshness": "unknown", "confidence": data_confidence}),
        "data_confidence": data_confidence, "provider_gaps_json": json_dumps(provider_gaps or []),
        "attachments_json": json_dumps(attachments or []), "markdown_body": body, "html_body_optional": html_body_optional,
        "tags": json_dumps(tags or []), "archived": 0, "created_at": now, "updated_at": now,
    }
    execute_query(
        """
        INSERT INTO report_inbox_items (report_id, report_type, title, summary, generated_at, linked_watchlist_items,
            linked_assets, linked_regions, linked_events, linked_strategy_commits, source_snapshot_json, data_confidence,
            provider_gaps_json, attachments_json, markdown_body, html_body_optional, tags, archived, created_at, updated_at)
        VALUES (:report_id, :report_type, :title, :summary, :generated_at, :linked_watchlist_items,
            :linked_assets, :linked_regions, :linked_events, :linked_strategy_commits, :source_snapshot_json, :data_confidence,
            :provider_gaps_json, :attachments_json, :markdown_body, :html_body_optional, :tags, :archived, :created_at, :updated_at)
        """, row, db_path=db_path)
    return get_report(row["report_id"], db_path) or _decode(row)


def get_report(report_id: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    row = execute_query("SELECT * FROM report_inbox_items WHERE report_id = ?", (report_id,), fetch=True, one=True, db_path=db_path)
    return _decode(row) if isinstance(row, dict) else None


def list_reports(include_archived: bool = False, limit: int = 100, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    where = "" if include_archived else "WHERE archived = 0"
    rows = execute_query(f"SELECT * FROM report_inbox_items {where} ORDER BY generated_at DESC LIMIT ?", (int(limit),), fetch=True, db_path=db_path)
    return [_decode(row) for row in rows]  # type: ignore[arg-type]


def archive_report(report_id: str, db_path: str | Path | None = None) -> bool:
    execute_query("UPDATE report_inbox_items SET archived = 1, updated_at = ? WHERE report_id = ?", (utc_now(), report_id), db_path=db_path)
    return True


def delete_report(report_id: str, db_path: str | Path | None = None) -> bool:
    return archive_report(report_id, db_path)


def search_reports(query: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    needle = f"%{str(query or '').lower()}%"
    rows = execute_query("SELECT * FROM report_inbox_items WHERE archived = 0 AND (lower(title) LIKE ? OR lower(summary) LIKE ? OR lower(tags) LIKE ?) ORDER BY generated_at DESC", (needle, needle, needle), fetch=True, db_path=db_path)
    return [_decode(row) for row in rows]  # type: ignore[arg-type]

