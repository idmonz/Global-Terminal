from lib.options_book_stress import aggregate_option_book_scenario_pnl, build_option_book_stress_snapshot


def _pos():
    return [{'underlying':'SPY','asset_class':'equity','option_type':'call','expiry':'2026-07-15','strike':100,'quantity':1,'position':'long','premium':7,'mark':8,'implied_volatility':0.25,'underlying_price':100,'time_to_expiry_years':0.2,'contract_multiplier':100,'source':'unit','timestamp':'2026-06-15'}]


def test_goal12c_option_book_stress_aggregates_scenario_pnl():
    out=aggregate_option_book_scenario_pnl(_pos(), price_shock=0.05)
    assert out['ok'] is True
    assert out['position_count'] == 1
    assert 'scenario_pnl' in out


def test_goal12c_option_book_stress_snapshot_has_grids():
    snap=build_option_book_stress_snapshot(_pos())
    assert snap['ok'] is True
    assert snap['price_shock_grid'] and snap['vol_shock_grid'] and snap['time_decay_grid']
    assert 'stress_report_not_advice' in snap['caveats']
