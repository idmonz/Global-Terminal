from lib.watchlist_store import create_watchlist_item
from lib.provider_snapshot_store import store_provider_health_snapshot
from lib.report_generators import generate_watchlist_brief, generate_provider_health_report, generate_strategy_review_report
from lib.strategy_decision_log import create_strategy_commit


def test_watchlist_brief_contains_linked_event_and_provider_caveat(tmp_path):
    db = tmp_path / "research.db"
    create_watchlist_item(item_type="chokepoint", display_name="Red Sea", tags=["energy"], db_path=db)
    store_provider_health_snapshot("FRED", status="missing_key", freshness="missing-key", confidence="low", missing_keys=["FRED_API_KEY"], db_path=db)
    report = generate_watchlist_brief(db_path=db, supplied_context={"events": [{"title": "Bab el-Mandeb shipping stress", "summary": "Red Sea energy route", "source": "mock"}]})
    body = report["markdown_body"]
    assert "Linked Events" in body
    assert "Bab el-Mandeb" in body
    assert "FRED_API_KEY" in body


def test_provider_health_report_uses_stored_snapshot(tmp_path):
    db = tmp_path / "research.db"
    store_provider_health_snapshot("EIA", status="stale", freshness="stale", confidence="medium", gaps=["weekly petroleum delayed"], db_path=db)
    report = generate_provider_health_report(db_path=db)
    assert "Provider Snapshot Memory" in report["markdown_body"]
    assert "EIA" in report["markdown_body"]
    assert "stale" in report["markdown_body"]


def test_strategy_review_report_includes_guard_warnings(tmp_path):
    db = tmp_path / "research.db"
    create_strategy_commit(strategy_id="ensemble_3", message="Research candidate", backtest_snapshot={"sample_size": 30, "max_drawdown": -35}, data_quality_snapshot={"status": "proxy", "score": 45}, db_path=db)
    report = generate_strategy_review_report(db_path=db)
    assert "Guard Warnings" in report["markdown_body"]
    assert "sample_length_guard" in report["markdown_body"] or "drawdown_guard" in report["markdown_body"]
