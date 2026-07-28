from lib.options_book_stress import aggregate_option_book_scenario_pnl

BASE = {
    "underlying": "SPY",
    "asset_class": "equity",
    "option_type": "call",
    "expiry": "2026-07-15",
    "strike": 100,
    "quantity": 1,
    "position": "long",
    "premium": 7,
    "mark": 8,
    "implied_volatility": 0.25,
    "underlying_price": 100,
    "contract_multiplier": 100,
    "source": "unit",
}


def test_goal12d_book_stress_derives_tte_from_expiry_timestamp():
    out = aggregate_option_book_scenario_pnl([{**BASE, "timestamp": "2026-06-15"}], price_shock=0.01)
    row = out["rows"][0]
    assert row["tte_status"] == "derived"
    assert row["repricing_status"] == "repriced"
    assert row["time_to_expiry_years"] > 0


def test_goal12d_book_stress_missing_tte_skips_repricing_not_30_day_default():
    out = aggregate_option_book_scenario_pnl([BASE], price_shock=0.01)
    row = out["rows"][0]
    assert row["tte_status"] == "missing_timestamp"
    assert row["repricing_status"] == "tte_missing_reprice_skipped"
    assert row["time_to_expiry_years"] is None
    assert row["scenario_price"] == BASE["mark"]


def test_goal12d_book_stress_expired_option_caveated():
    out = aggregate_option_book_scenario_pnl([{**BASE, "timestamp": "2026-08-15"}], price_shock=0.01)
    row = out["rows"][0]
    assert row["tte_status"] == "expired"
    assert row["repricing_status"] == "expired_option"
