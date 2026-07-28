from lib.headless_report_runner import REPORT_GENERATORS, run_report_generator


def test_headless_report_runner(tmp_path):
    db=tmp_path/"h.db"
    assert "watchlist" in REPORT_GENERATORS
    assert run_report_generator("watchlist", db)["report_type"] == "Watchlist Brief"

