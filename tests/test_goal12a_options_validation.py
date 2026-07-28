import pytest

from lib.options_validation import validate_option_input


def test_validation_rejects_negative_volatility():
    with pytest.raises(ValueError):
        validate_option_input({"option_type": "call", "underlying_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": -0.2})


def test_validation_rejects_non_positive_underlying_and_strike():
    with pytest.raises(ValueError):
        validate_option_input({"option_type": "call", "underlying_price": 0, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2})
    with pytest.raises(ValueError):
        validate_option_input({"option_type": "call", "underlying_price": 100, "strike": 0, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2})


def test_validation_rejects_non_positive_time():
    with pytest.raises(ValueError):
        validate_option_input({"option_type": "call", "underlying_price": 100, "strike": 100, "time_to_expiry_years": 0, "risk_free_rate": 0.05, "volatility": 0.2})
