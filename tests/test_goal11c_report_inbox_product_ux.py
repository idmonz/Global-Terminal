from lib.report_inbox import create_report, get_report
from lib.report_inbox_page_layout import build_report_inbox_page_payload
from lib.report_reader_panel import build_report_reader_panel
from lib.report_review_workflow import update_report_review_status
from lib.report_source_caveat_panel import build_report_source_caveat_panel


def test_goal11c_report_reader_review_and_source_caveats(tmp_path):
    db = tmp_path / "workspace.db"
    report = create_report(
        report_type="watchlist",
        title="Watchlist Brief <script>",
        summary="summary",
        markdown_body="# Hello",
        html_body_optional="<script>alert(1)</script>",
        provider_gaps=["missing provider key"],
        db_path=db,
    )
    payload = build_report_inbox_page_payload(db)
    assert payload["sidebar"]["items"]
    assert payload["reader_panel"]["review_status"] == "unread"
    reader = build_report_reader_panel(report)
    assert "&lt;script&gt;" in reader["safe_preview"]
    panel = build_report_source_caveat_panel(report)
    assert panel["gaps"] == ["missing provider key"]
    updated = update_report_review_status(report["report_id"], "reviewed", notes="checked", db_path=db)
    assert updated["ok"] is True
    assert get_report(report["report_id"], db)["report_review_status"] == "reviewed"
