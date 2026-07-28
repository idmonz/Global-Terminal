from lib.scheduled_briefing_engine import generate_watchlist_brief, generate_provider_health_report


def test_manual_report_generators(tmp_path):
    db=tmp_path/"g.db"
    assert generate_watchlist_brief(db)["report_type"] == "Watchlist Brief"
    assert generate_provider_health_report(db)["report_type"] == "Provider Health Report"

