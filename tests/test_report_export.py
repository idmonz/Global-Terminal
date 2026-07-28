from lib.report_inbox import create_report
from lib.report_export import export_report_html, export_report_markdown


def test_report_export(tmp_path):
    db=tmp_path/"e.db"
    report=create_report(report_type="Watchlist Brief", title="Export", db_path=db)
    md=export_report_markdown(report["report_id"], tmp_path/"out.md", db)
    html=export_report_html(report["report_id"], tmp_path/"out.html", db)
    assert md.exists() and html.exists()

