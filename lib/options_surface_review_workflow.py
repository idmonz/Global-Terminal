from __future__ import annotations
from pathlib import Path
from typing import Any

from .options_surface_review_queue import create_surface_review_item, update_surface_review_status, build_surface_review_queue, build_surface_review_cards
from .report_inbox import create_report
from .strategy_decision_log import attach_report_to_commit


def attach_surface_review_to_report(review_item: dict[str, Any], *, db_path: str | Path | None = None) -> dict[str, Any]:
    report = create_report(
        report_type="options_surface_qa_report",
        title=f"Surface QA Review: {review_item.get('title', 'Surface QA')}",
        summary=f"Surface QA review status: {review_item.get('status')}; anomalies: {review_item.get('anomaly_count', 0)}.",
        attachments=[{"type": "surface_review_item", "payload": review_item, "research_only": True}],
        markdown_body="# Surface QA Review\n\nResearch-only surface QA review item attached.\n",
        tags=["options", "surface_qa", "review_queue"],
        db_path=db_path,
    )
    return {"ok": True, "report": report, "report_id": report.get("report_id"), "review_id": review_item.get("review_id"), "research_only": True}


def attach_surface_review_to_strategy_commit(review_item: dict[str, Any], commit_id: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    attached = attach_surface_review_to_report(review_item, db_path=db_path)
    commit = attach_report_to_commit(commit_id, attached["report_id"], db_path=db_path)
    return {"ok": commit is not None, "commit": commit, "report_id": attached["report_id"], "review_id": review_item.get("review_id"), "research_only": True}


def build_surface_review_workflow_payload(items: list[dict[str, Any]]) -> dict[str, Any]:
    queue = build_surface_review_queue(items)
    return {**queue, "cards": build_surface_review_cards(queue["items"]), "research_only": True}
