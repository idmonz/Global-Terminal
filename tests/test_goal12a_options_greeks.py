from lib.options_greeks import calculate_greeks


def test_black_scholes_greeks_reference_values():
    result = calculate_greeks({"option_type": "call", "underlying_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2})
    greeks = result["greeks"]
    assert round(greeks["delta"], 6) == 0.636831
    assert round(greeks["gamma"], 6) == 0.018762
    assert round(greeks["vega"], 6) == 37.524035
    assert "theta_per_day" in greeks
    assert "carry_or_dividend_sensitivity" in greeks


def test_black76_greeks_available():
    result = calculate_greeks({"model": "black_76", "option_type": "put", "underlying_price": 100, "futures_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2})
    assert result["greeks"]["delta"] < 0
    assert result["greeks"]["vega"] > 0
