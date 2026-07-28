from __future__ import annotations

from html import escape
import re
from typing import Any


def _escape_text(value: Any) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def sanitize_optional_report_html(html_body: Any) -> str:
    """Return a safe representation of optional HTML.

    Goal 11F treats report HTML as an untrusted boundary. Instead of
    preserving arbitrary tags/attributes, it stores the supplied HTML as
    escaped text inside a local report article so scripts, event handlers,
    and javascript: URLs cannot execute in exported files.
    """
    return _escape_text(html_body)


def _render_markdown_lines(markdown_body: Any) -> str:
    raw = str(markdown_body if markdown_body is not None else "")
    lines = raw.splitlines()
    html: list[str] = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html.append("</ul>")
                in_list = False
            html.append("")
            continue
        if stripped.startswith("### "):
            if in_list:
                html.append("</ul>")
                in_list = False
            html.append(f"<h3>{_escape_text(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            if in_list:
                html.append("</ul>")
                in_list = False
            html.append(f"<h2>{_escape_text(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            if in_list:
                html.append("</ul>")
                in_list = False
            html.append(f"<h1>{_escape_text(stripped[2:])}</h1>")
        elif stripped.startswith(("- ", "* ")):
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f"<li>{_escape_text(stripped[2:])}</li>")
        else:
            if in_list:
                html.append("</ul>")
                in_list = False
            safe = _escape_text(stripped)
            # Preserve Markdown emphasis readability without allowing HTML.
            safe = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", safe)
            html.append(f"<p>{safe}</p>")
    if in_list:
        html.append("</ul>")
    return "\n".join(line for line in html if line != "")


def render_safe_report_export_html(*, title: str = "Research Report", markdown_body: Any = "", html_body_optional: Any = "") -> str:
    safe_title = _escape_text(title)
    if html_body_optional:
        body = (
            "<section class=\"escaped-html-preview\">"
            "<h2>Escaped optional HTML preview</h2>"
            "<pre>" + sanitize_optional_report_html(html_body_optional) + "</pre>"
            "</section>"
        )
    else:
        body = "<section class=\"markdown-report\">" + _render_markdown_lines(markdown_body) + "</section>"
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{safe_title}</title>"
        "<style>body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.55;margin:2rem;}"
        "pre{white-space:pre-wrap;background:#f7f7f8;padding:1rem;border-radius:8px;}"
        "article{max-width:960px;margin:auto;} .caveat{color:#555;font-size:.9rem;}</style>"
        "</head><body><article>"
        f"<header><h1>{safe_title}</h1><p class=\"caveat\">Safe local research export. Unsafe HTML is escaped by default.</p></header>"
        f"{body}</article></body></html>"
    )


def render_safe_report_html(markdown_body: str, title: str = "Research Report") -> str:
    safe_title = _escape_text(title)
    return (
        "<article>"
        f"<header><h1>{safe_title}</h1><p class=\"caveat\">Safe local research preview. Unsafe HTML is escaped by default.</p></header>"
        "<section class=\"markdown-report\">"
        + _render_markdown_lines(markdown_body)
        + "</section></article>"
    )
