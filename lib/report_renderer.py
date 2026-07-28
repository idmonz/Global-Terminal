from __future__ import annotations
from typing import Any
from .report_markdown_templates import render_type_specific_markdown
from .report_html_templates import render_safe_report_html


def render_report_markdown(context: dict[str, Any], title: str | None = None) -> str:
    report_title = title or context.get("report_type", "Research Report")
    return render_type_specific_markdown(context, report_title)


def render_report_html(context: dict[str, Any], title: str | None = None) -> str:
    md = render_report_markdown(context, title)
    return render_safe_report_html(md, title or context.get("report_type", "Research Report"))
