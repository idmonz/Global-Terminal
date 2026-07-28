from lib.options_data_quality import build_options_data_quality_status
from lib.options_provider_capabilities import build_options_provider_capability, inspect_options_provider_capabilities


def test_manual_provider_caveat_and_no_live_data_claim():
    card = build_options_provider_capability("manual", used_for_calculation=True)
    assert card["used_for_calculation"] is True
    assert "No live option chain" in card["caveat"]


def test_missing_chain_data_quality_caveat():
    status = build_options_data_quality_status({"underlying_price": 100}, option_chain_supplied=False)
    assert status["ok"] is False
    assert status["missing_fields"]
    assert inspect_options_provider_capabilities()["ok"] is True
