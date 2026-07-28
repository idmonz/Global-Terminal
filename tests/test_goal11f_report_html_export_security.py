from lib.report_export import export_report_html
from lib.report_html_templates import render_safe_report_export_html, sanitize_optional_report_html
from lib.report_inbox import create_report


def test_goal11f_optional_html_body_is_never_exported_raw(tmp_path):
    db = tmp_path / "workspace.db"
    report = create_report(
        report_type="security_test",
        title="Unsafe Optional HTML",
        markdown_body="# Safe fallback\n\n- item",
        html_body_optional='<h1>Unsafe</h1><script>alert(1)</script><img src=x onerror=alert(2)><a href="javascript:alert(3)">x</a>',
        db_path=db,
    )
    target = tmp_path / "report.html"
    export_report_html(report["report_id"], target, db_path=db)
    text = target.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "<script" not in lowered
    assert "<img" not in lowered
    assert 'href="javascript:' not in lowered
    assert "&lt;script" in lowered or "script" not in lowered
    assert "escaped optional html preview" in lowered


def test_goal11f_markdown_fallback_remains_readable_and_safe():
    html = render_safe_report_export_html(title="T", markdown_body="# Heading\n\n- One\n\n<script>x</script>")
    lowered = html.lower()
    assert "<h1>heading</h1>" in lowered
    assert "<li>one</li>" in lowered
    assert "<script" not in lowered
    assert "&lt;script&gt;" in lowered


def test_goal11f_sanitize_optional_html_escapes_event_handlers_and_urls():
    safe = sanitize_optional_report_html('<img src=x onerror=alert(1)><a href="javascript:alert(2)">x</a>')
    assert "<img" not in safe.lower()
    assert "&lt;img" in safe.lower()
    assert 'href="javascript:' not in safe.lower()
