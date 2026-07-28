from lib.options_chain_validation import validate_option_chain_rows


def test_option_chain_validation_rejects_crossed_market_and_bad_side():
    result = validate_option_chain_rows([
        {"underlying":"X","expiry":"2026-12-31","strike":100,"option_type":"C","bid":7,"ask":6,"underlying_price":100,"timestamp":"2026-06-15T00:00:00Z","source":"test"},
        {"underlying":"X","expiry":"2026-12-31","strike":100,"option_type":"bad","bid":1,"ask":2,"underlying_price":100,"timestamp":"2026-06-15T00:00:00Z","source":"test"},
    ])
    assert result["accepted_count"] == 0
    assert result["rejected_count"] == 2
    assert "bid_greater_than_ask" in result["rejected_rows"][0]["errors"]
