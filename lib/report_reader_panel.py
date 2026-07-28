from __future__ import annotations

from typing import Any

from .source_freshness_strip import build_source_freshness_strip
from .streamlit_research_renderers import sanitize_html_preview, sanitize_markdown_text


def build_report_reader_panel(report: dict[str, Any] | None = None) -> dict[str, Any]:
    if not report:
        return {"title": "No report selected", "empty": True, "message": "Generate or select a report to begin review.", "research_only": True}
    markdown = str(report.get("markdown_body") or "")
    safe_html = sanitize_html_preview(str(report.get("html_body_optional") or markdown))
    return {
        "report_id": report.get("report_id"),
        "title": report.get("title", "Untitled report"),
        "summary": report.get("summary", ""),
        "report_type": report.get("report_type", "unknown"),
        "generated_at": report.get("generated_at", ""),
        "markdown_body": sanitize_markdown_text(markdown),
        "safe_preview": safe_html,
        "review_status": report.get("report_review_status") or "unread",
        "review_notes": report.get("review_notes") or "",
        "source_freshness": build_source_freshness_strip(report.get("source_snapshot_json", {}), title="Report source freshness"),
        "linked": {
            "watchlist_items": report.get("linked_watchlist_items", []),
            "events": report.get("linked_events", []),
            "strategy_commits": report.get("linked_strategy_commits", []),
        },
        "raw_payload_available": True,
        "research_only": True,
    }
