from lib.alert_store import create_alert_rule
from lib.alert_evaluator import evaluate_alert_rule, evaluate_all_alerts


def test_alert_evaluator_missing_data_no_false_trigger(tmp_path):
    db=tmp_path/"ae.db"
    rule=create_alert_rule(scope="price", metric="close", operator="above", threshold=100, db_path=db)
    result=evaluate_alert_rule(rule, {}, persist=True, db_path=db)
    assert result["triggered"] is False
    assert result["status"] == "skipped_data_gap"
    assert evaluate_all_alerts({"close":101}, db_path=db)[0]["triggered"] is True

