from lib.watchlist_models import infer_item_type, validate_watchlist_item_type
import pytest


def test_watchlist_model_types():
    assert infer_item_type("BTCUSDT") == "crypto"
    assert infer_item_type("Provider: FRED") == "provider"
    with pytest.raises(ValueError): validate_watchlist_item_type("broker_order")

