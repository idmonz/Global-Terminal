from lib.options_pricing_models import black_scholes_price
from lib.options_iv_solver import implied_volatility
from lib.options_strategy_templates import build_strategy_payoff


def test_goal12a_core_still_prices_solves_iv_and_builds_payoff():
    price=black_scholes_price("call", 100, 100, 1, 0.05, 0.2)
    assert round(price, 4) == 10.4506
    iv=implied_volatility({"option_type":"call","underlying_price":100,"strike":100,"time_to_expiry_years":1,"risk_free_rate":0.05,"volatility":0.2}, market_price=price)
    assert iv["ok"] is True
    payoff=build_strategy_payoff("straddle", {"strike":100,"call_premium":5,"put_premium":5,"price_grid":[80,100,120]})
    assert payoff["strategy_template"] == "straddle"
