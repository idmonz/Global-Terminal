from lib.alert_rules import build_alert_rule_template, validate_alert_operator, validate_alert_scope
import pytest


def test_alert_rule_validation():
    assert build_alert_rule_template("price", "close", "above", 100)["operator"] == "above"
    with pytest.raises(ValueError): validate_alert_scope("broker")
    with pytest.raises(ValueError): validate_alert_operator("execute")

