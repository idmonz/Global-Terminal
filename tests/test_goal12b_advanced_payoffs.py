from lib.options_advanced_payoffs import butterfly, calendar_spread, custom_multi_leg_payoff, diagonal_spread, iron_condor, ratio_spread
from lib.options_strategy_templates import build_strategy_payoff, list_option_strategy_templates


def test_advanced_payoff_templates_return_grid_limited_metrics():
    grid = [80, 90, 100, 110, 120]
    assert calendar_spread(100, 2, 4, grid)["strategy_template"] == "calendar_spread"
    assert diagonal_spread(100, 105, 2, 4, grid)["expiry_caveat"]
    assert butterfly(100, 5, 1, 2, 1, grid)["ok"] is True
    assert iron_condor(90, 95, 105, 110, {"lower_put":1,"short_put":2,"short_call":2,"upper_call":1}, grid)["ok"] is True
    assert ratio_spread(100, 105, 2, 1, 2, grid)["ratio_spread_caveat"]
    assert custom_multi_leg_payoff([{"option_type":"call","strike":100,"premium":5,"position":"long"}], grid)["ok"] is True
    names = [x["template"] for x in list_option_strategy_templates()]
    assert "calendar_spread" in names and "custom_multi_leg" in names
    assert build_strategy_payoff("calendar_spread", {"strike":100,"near_premium":2,"far_premium":4,"price_grid":grid})["ok"] is True
