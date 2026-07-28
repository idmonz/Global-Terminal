from lib.research_attachment_models import ATTACHMENT_TYPES, build_research_attachment, validate_attachment_type
import pytest


def test_research_attachment_models():
    assert "option_analysis_snapshot" in ATTACHMENT_TYPES
    assert build_research_attachment("quant_model_snapshot", "Model")["attachment_type"] == "quant_model_snapshot"
    with pytest.raises(ValueError): validate_attachment_type("live_order")

