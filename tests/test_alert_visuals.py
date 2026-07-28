from lib.alert_visuals import build_alert_summary_cards, build_alert_timeline, build_alerts_for_watchlist_item


def test_alert_visuals():
    rules=[{"active":True,"watch_item_id":"w"}]; events=[{"triggered":True,"created_at":"2","watch_item_id":"w"},{"triggered":False,"status":"skipped_data_gap","created_at":"1"}]
    assert build_alert_summary_cards(rules, events)[0]["value"] == 1
    assert build_alert_timeline(events)[0]["created_at"] == "2"
    assert build_alerts_for_watchlist_item("w", rules, events)["rules"]

