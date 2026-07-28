from lib.alert_store import create_alert_rule, list_alert_events
from lib.research_workflow_actions import run_research_workflow_action


def test_goal11e_alert_evaluation_uses_alert_engine_with_supplied_context(tmp_path):
    db = tmp_path / "workspace.db"
    create_alert_rule(watch_item_id="watch_btc", metric="close", operator="above", threshold="100", cooldown_minutes=0, db_path=db)
    result = run_research_workflow_action("EVALUATE_ALERTS_NOW", {"data_context": {"close": 125}, "source_snapshot": {"freshness": "fresh"}}, db_path=db)
    assert result["ok"] is True
    assert result["evaluated_alert_rules"] == 1
    assert result["triggered_count"] == 1
    assert result["events_created"] == 1
    assert len(list_alert_events(db_path=db)) == 1


def test_goal11e_alert_evaluation_missing_context_is_caveated_skip(tmp_path):
    db = tmp_path / "workspace.db"
    create_alert_rule(watch_item_id="watch_btc", metric="close", operator="above", threshold="100", db_path=db)
    result = run_research_workflow_action("EVALUATE_ALERTS_NOW", {}, db_path=db)
    assert result["ok"] is True
    assert result["status"] == "skipped_unavailable"
    assert result["events_created"] == 0
    assert len(list_alert_events(db_path=db)) == 0


def test_goal11e_alert_evaluation_missing_metric_creates_no_false_trigger(tmp_path):
    db = tmp_path / "workspace.db"
    create_alert_rule(watch_item_id="watch_btc", metric="close", operator="above", threshold="100", db_path=db)
    result = run_research_workflow_action("EVALUATE_ALERTS_NOW", {"data_context": {"volume": 999}}, db_path=db)
    assert result["ok"] is True
    assert result["triggered_count"] == 0
    assert result["skipped_data_gap_count"] == 1
    assert result["events_created"] == 0


def test_goal11e_alert_evaluation_dedupe_prevents_duplicate_event(tmp_path):
    db = tmp_path / "workspace.db"
    create_alert_rule(watch_item_id="watch_btc", metric="close", operator="above", threshold="100", cooldown_minutes=0, db_path=db)
    first = run_research_workflow_action("EVALUATE_ALERTS_NOW", {"data_context": {"close": 125}}, db_path=db)
    second = run_research_workflow_action("EVALUATE_ALERTS_NOW", {"data_context": {"close": 125}}, db_path=db)
    assert first["events_created"] == 1
    assert second["events_created"] == 0
    assert len(list_alert_events(db_path=db)) == 1
