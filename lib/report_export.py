from __future__ import annotations
from pathlib import Path
from .report_inbox import get_report
from .report_html_templates import render_safe_report_export_html, sanitize_optional_report_html
from .research_workspace_paths import get_private_report_dir


def export_report_markdown(report_id: str, path: str | Path | None = None, db_path: str | Path | None = None) -> Path:
    report = get_report(report_id, db_path)
    if not report: raise ValueError(f"Report not found: {report_id}")
    target = Path(path) if path else get_private_report_dir() / f"{report_id}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.get("markdown_body", ""), encoding="utf-8")
    return target


def export_report_html(report_id: str, path: str | Path | None = None, db_path: str | Path | None = None) -> Path:
    report = get_report(report_id, db_path)
    if not report: raise ValueError(f"Report not found: {report_id}")
    target = Path(path) if path else get_private_report_dir() / f"{report_id}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    html = render_safe_report_export_html(
        title=report.get("title", "Research Report"),
        markdown_body=report.get("markdown_body", ""),
        html_body_optional=report.get("html_body_optional", ""),
    )
    target.write_text(html, encoding="utf-8")
    return target


__all__ = ["export_report_markdown", "export_report_html", "sanitize_optional_report_html", "render_safe_report_export_html"]
