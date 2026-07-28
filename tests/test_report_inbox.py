from lib.report_inbox import archive_report, create_report, get_report, list_reports, search_reports


def test_report_inbox(tmp_path):
    db=tmp_path/"r.db"
    report=create_report(report_type="Watchlist Brief", title="Test Watchlist Brief", summary="summary", db_path=db)
    assert get_report(report["report_id"], db)["title"] == "Test Watchlist Brief"
    assert search_reports("watchlist", db)
    archive_report(report["report_id"], db)
    assert list_reports(db_path=db) == []

