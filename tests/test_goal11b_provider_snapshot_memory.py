from lib.provider_snapshot_store import store_provider_health_snapshot, list_provider_health_snapshots, get_latest_provider_health_snapshot
from lib.data_quality_snapshot_store import store_data_quality_snapshot, get_latest_data_quality_snapshot
from lib.provider_report_memory import build_provider_report_memory, build_data_quality_report_memory
from lib.watchlist_store import create_watchlist_item
from lib.watchlist_engine import build_watchlist_context
from lib.alert_store import create_alert_rule
from lib.alert_evaluator import evaluate_alert_rule


def test_provider_and_data_quality_snapshot_storage_latest(tmp_path):
    db = tmp_path / "research.db"
    store_provider_health_snapshot("FRED", status="missing_key", freshness="missing-key", confidence="low", missing_keys=["FRED_API_KEY"], db_path=db)
    assert list_provider_health_snapshots("FRED", db_path=db)
    assert get_latest_provider_health_snapshot("FRED", db_path=db)["status"] == "missing_key"
    store_data_quality_snapshot("macro", status="proxy", freshness="aging", confidence="medium", gaps=["series proxy"], db_path=db)
    assert get_latest_data_quality_snapshot("macro", db_path=db)["status"] == "proxy"
    assert build_provider_report_memory(db_path=db)["gap_count"] == 1
    assert build_data_quality_report_memory(db_path=db)["gap_count"] == 1


def test_provider_watchlist_linking_and_alert_evaluation(tmp_path):
    db = tmp_path / "research.db"
    item = create_watchlist_item(item_type="provider", symbol="FRED", display_name="Provider: FRED", db_path=db)
    store_provider_health_snapshot("FRED", status="stale", freshness="stale", confidence="low", db_path=db)
    ctx = build_watchlist_context(db)
    provider_row = [r for r in ctx["enriched_items"] if r["item_id"] == item["item_id"]][0]
    assert provider_row["source_status"] == "stale"
    rule = create_alert_rule(watch_item_id=item["item_id"], scope="provider", metric="source_freshness", operator="stale_for", threshold="1h", db_path=db)
    result = evaluate_alert_rule(rule, {}, persist=True, db_path=db)
    assert result["triggered"] is True
