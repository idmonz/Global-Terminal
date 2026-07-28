from lib.options_scenarios import build_price_shock_grid, option_scenario_grid


def test_price_shock_grid_is_deterministic():
    assert build_price_shock_grid(100, [-0.1, 0, 0.1]) == [90.0, 100.0, 110.00000000000001]


def test_option_scenario_grid_counts_rows_and_pnl():
    result = option_scenario_grid({"option_type": "call", "underlying_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2, "premium": 10}, price_grid=[90, 100], volatility_grid=[0.2, 0.3], time_grid=[1], rate_grid=[0.05])
    assert result["scenario_count"] == 4
    assert all("pnl_from_supplied_premium" in row for row in result["rows"])
