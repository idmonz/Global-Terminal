from lib.alert_store import create_alert_rule, list_alert_rules, delete_alert_rule, store_alert_event, list_alert_events


def test_alert_store(tmp_path):
    db=tmp_path/"a.db"
    rule=create_alert_rule(scope="price", metric="close", operator="above", threshold=100, db_path=db)
    assert list_alert_rules(db_path=db)
    store_alert_event({"alert_id":rule["alert_id"],"status":"skipped_data_gap","triggered":False,"message":"gap"}, db_path=db)
    assert list_alert_events(db_path=db)[0]["status"] == "skipped_data_gap"
    delete_alert_rule(rule["alert_id"], db)
    assert list_alert_rules(db_path=db) == []

