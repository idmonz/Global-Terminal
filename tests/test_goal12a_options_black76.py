from lib.options_pricing_models import black_76_price, price_option


def test_black76_known_reference_values():
    assert round(black_76_price("call", 100, 100, 1, 0.05, 0.20), 6) == 7.577082
    assert round(black_76_price("put", 100, 100, 1, 0.05, 0.20), 6) == 7.577082


def test_black76_uses_futures_price():
    result = price_option({"model": "black_76", "option_type": "call", "underlying_price": 100, "futures_price": 105, "strike": 100, "time_to_expiry_years": 0.5, "risk_free_rate": 0.03, "volatility": 0.25})
    assert result["model"] == "black_76"
    assert result["price"] > 0
