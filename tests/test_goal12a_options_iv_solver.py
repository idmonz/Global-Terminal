from lib.options_iv_solver import implied_volatility


def test_implied_volatility_converges_to_reference_vol():
    result = implied_volatility({"option_type": "call", "underlying_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2}, market_price=10.450583572185565)
    assert result["converged"] is True
    assert abs(result["implied_volatility"] - 0.2) < 1e-6


def test_implied_volatility_reports_no_solution_without_fake_value():
    result = implied_volatility({"option_type": "call", "underlying_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2}, market_price=0.00001)
    assert result["ok"] is False
    assert result["implied_volatility"] is None
    assert result["error_reason"]
