from datetime import datetime, timezone, timedelta
from lib.alert_store import create_alert_rule, get_alert_rule, list_alert_events
from lib.alert_evaluator import evaluate_alert_rule


def test_alert_cooldown_blocks_duplicate_trigger(tmp_path):
    db = tmp_path / "research.db"
    rule = create_alert_rule(metric="close", operator="above", threshold=100, cooldown_minutes=60, db_path=db)
    first = evaluate_alert_rule(rule, {"close": 110}, persist=True, db_path=db)
    assert first["triggered"] is True
    second_rule = get_alert_rule(rule["alert_id"], db)
    second = evaluate_alert_rule(second_rule, {"close": 120}, persist=True, db_path=db)
    assert second["status"] == "skipped_cooldown"
    assert len([e for e in list_alert_events(db_path=db) if e["triggered"]]) == 1


def test_alert_expiry_skips_evaluation(tmp_path):
    db = tmp_path / "research.db"
    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rule = create_alert_rule(metric="close", operator="above", threshold=100, expires_at=expired, db_path=db)
    result = evaluate_alert_rule(rule, {"close": 150}, persist=True, db_path=db)
    assert result["status"] == "skipped_expired"
    assert result["triggered"] is False


def test_alert_crosses_above_uses_previous_value(tmp_path):
    db = tmp_path / "research.db"
    rule = create_alert_rule(metric="close", operator="crosses_above", threshold=100, db_path=db)
    first = evaluate_alert_rule(rule, {"close": 90}, persist=True, db_path=db)
    assert first["triggered"] is False
    updated = get_alert_rule(rule["alert_id"], db)
    second = evaluate_alert_rule(updated, {"close": 105}, persist=True, db_path=db)
    assert second["triggered"] is True
    assert second["previous_observed_value"] == "90" or float(second["previous_observed_value"]) == 90


def test_missing_metric_does_not_trigger(tmp_path):
    db = tmp_path / "research.db"
    rule = create_alert_rule(metric="funding", operator="above", threshold=0.05, db_path=db)
    result = evaluate_alert_rule(rule, {}, persist=True, db_path=db)
    assert result["status"] == "skipped_data_gap"
    assert result["triggered"] is False
