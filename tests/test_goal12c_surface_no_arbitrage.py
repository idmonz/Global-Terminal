from lib.options_surface_arbitrage import check_butterfly_convexity, check_call_put_parity_diagnostics, check_calendar_monotonicity, check_vertical_monotonicity


def _surface():
    return {'points':[{'expiry':'2026-07-15','strike':90.0,'option_type':'call','mid_iv':0.2,'moneyness':0.9,'days_to_expiry':30},{'expiry':'2026-07-15','strike':100.0,'option_type':'call','mid_iv':1.4,'moneyness':1.0,'days_to_expiry':30},{'expiry':'2026-07-15','strike':110.0,'option_type':'call','mid_iv':0.2,'moneyness':1.1,'days_to_expiry':30},{'expiry':'2026-07-15','strike':100.0,'option_type':'put','mid_iv':0.3,'moneyness':1.0,'days_to_expiry':30}]}


def test_goal12c_surface_arbitrage_diagnostics_return_anomalies():
    s=_surface()
    assert check_vertical_monotonicity(s)['ok'] is True
    assert check_butterfly_convexity(s)['anomaly_count'] >= 1
    assert check_calendar_monotonicity(s)['ok'] is True
    assert check_call_put_parity_diagnostics(s)['missing_pair_count'] >= 1
