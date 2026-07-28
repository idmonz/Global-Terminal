from lib.alert_engine import create_alert_rule, evaluate_all_alerts


def test_alert_engine_exports(tmp_path):
    db=tmp_path/"engine.db"
    create_alert_rule(scope="price", metric="px", operator="below", threshold=10, db_path=db)
    assert evaluate_all_alerts({"px":9}, db_path=db)[0]["triggered"] is True

