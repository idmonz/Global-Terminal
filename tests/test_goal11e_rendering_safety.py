from lib.report_export import export_report_html
from lib.report_inbox import create_report
from lib.report_reader_panel import build_report_reader_panel
from lib.streamlit_research_renderers import render_report_reader, render_safe_markdown, sanitize_html_preview, sanitize_markdown_text


def test_goal11e_markdown_headings_remain_readable_and_scripts_escape():
    safe = sanitize_markdown_text("# Heading\n\n<script>alert(1)</script>")
    assert safe.startswith("# Heading")
    assert "<script>" not in safe
    assert "&lt;script&gt;" in safe
    rendered = render_safe_markdown("## Subheading\nText")
    assert rendered["markdown"].startswith("## Subheading")


def test_goal11e_user_supplied_html_preview_is_escaped():
    preview = sanitize_html_preview("<img src=x onerror=alert(1)>")
    assert "<img" not in preview
    assert "&lt;img" in preview


def test_goal11e_report_reader_and_export_keep_scripts_escaped(tmp_path):
    db = tmp_path / "workspace.db"
    report = create_report(report_type="watchlist", title="Safety", markdown_body="# Safe\n<script>alert(1)</script>", db_path=db)
    panel = build_report_reader_panel(report)
    assert panel["markdown_body"].startswith("# Safe")
    assert "<script>" not in panel["markdown_body"]
    rendered = render_report_reader(panel)
    assert "&lt;script&gt;" in rendered["payload"]["safe_markdown"]
    out = tmp_path / "report.html"
    export_report_html(report["report_id"], out, db_path=db)
    assert "<script>" not in out.read_text(encoding="utf-8")
