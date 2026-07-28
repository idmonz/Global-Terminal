from lib.research_command_safety import detect_forbidden_command_intent
from lib.options_book_stress import build_option_book_stress_snapshot
from lib.options_model_selector import infer_option_pricing_model_for_row
from lib.options_surface_price_checks import check_option_price_convexity_by_strike


def test_goal12e_goal12d_public_boundaries_preserved():
    assert detect_forbidden_command_intent("go long BTC")["blocked"] is True
    stress = build_option_book_stress_snapshot([{"position_id": "p1", "underlying": "BTC", "option_type": "call", "expiry": "2026-07-15", "strike": 100, "quantity": 1, "position": "long", "premium": 4, "mark": 5, "underlying_price": 100, "implied_volatility": 0.2}])
    assert "tte_missing_reprice_skipped" in str(stress)
    assert infer_option_pricing_model_for_row({"asset_class": "unknown"})["ok"] is False
    assert check_option_price_convexity_by_strike({"points": []})["caveat"] == "price_check_unavailable"
