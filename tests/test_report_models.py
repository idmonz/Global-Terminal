from lib.report_models import REPORT_CAVEAT, build_report_source_snapshot, validate_report_type


def test_report_models():
    assert validate_report_type("Watchlist Brief") == "Watchlist Brief"
    assert build_report_source_snapshot("local", "fresh")["freshness"] == "fresh"
    assert "stale" in REPORT_CAVEAT

