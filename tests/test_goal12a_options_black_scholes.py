from lib.options_pricing_models import black_scholes_price, price_option


def test_black_scholes_known_reference_values():
    call = black_scholes_price("call", 100, 100, 1, 0.05, 0.20, 0.0)
    put = black_scholes_price("put", 100, 100, 1, 0.05, 0.20, 0.0)
    assert round(call, 6) == 10.450584
    assert round(put, 6) == 5.573526


def test_price_option_contract_value_and_notice():
    result = price_option({"option_type": "call", "underlying_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2, "contract_multiplier": 10})
    assert result["ok"] is True
    assert round(result["contract_value"], 6) == round(result["price"] * 10, 6)
    assert result["research_only"] is True
