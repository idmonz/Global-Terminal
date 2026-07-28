from lib.options_pricing_models import garman_kohlhagen_price, price_option


def test_garman_kohlhagen_known_reference_value():
    value = garman_kohlhagen_price("call", 1.25, 1.2, 0.5, 0.03, 0.01, 0.12)
    assert round(value, 6) == 0.079007


def test_garman_kohlhagen_alias_fields():
    result = price_option({"model": "garman_kohlhagen", "option_type": "put", "underlying_price": 1.25, "strike": 1.2, "time_to_expiry_years": 0.5, "risk_free_rate": 0.03, "domestic_rate": 0.03, "foreign_rate": 0.01, "volatility": 0.12})
    assert result["model"] == "garman_kohlhagen"
    assert result["price"] > 0
