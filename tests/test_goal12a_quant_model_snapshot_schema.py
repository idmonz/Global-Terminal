import pytest

from lib.quant_model_snapshot_schema import build_model_snapshot, validate_model_category


def test_quant_model_snapshot_schema_accepts_known_category():
    snapshot = build_model_snapshot("m1", "Model One", "option_model", diagnostics={"count": 1})
    assert snapshot["category"] == "option_model"
    assert snapshot["research_only"] is True


def test_quant_model_snapshot_schema_rejects_unknown_category():
    with pytest.raises(ValueError):
        validate_model_category("broker_runtime")
