from lib.options_lab_workflow_actions import run_options_lab_action


def test_goal12c_surface_qa_and_book_stress_workflow_actions():
    surface={'points':[{'expiry':'e1','strike':100.0,'option_type':'call','mid_iv':0.2,'moneyness':1.0,'pricing_model':'black_scholes'}]}
    qa=run_options_lab_action('BUILD_SURFACE_QA', {'surface_snapshot': surface})
    assert qa['ok'] is True and 'score' in qa
    stress=run_options_lab_action('BUILD_OPTION_BOOK_STRESS', {'positions':[{'underlying':'SPY','option_type':'call','expiry':'2026-07-15','strike':100,'quantity':1,'position':'long','premium':5,'mark':6,'implied_volatility':0.2,'underlying_price':100,'time_to_expiry_years':0.2,'contract_multiplier':100,'source':'unit','timestamp':'x'}]})
    assert stress['ok'] is True and stress['price_shock_grid']


def test_goal12c_surface_diff_and_quant_workflow_actions():
    prev={'points':[{'expiry':'e1','strike':100.0,'option_type':'call','mid_iv':0.2,'moneyness':1.0}]}
    cur={'points':[{'expiry':'e1','strike':100.0,'option_type':'call','mid_iv':0.3,'moneyness':1.0}]}
    diff=run_options_lab_action('BUILD_SURFACE_DIFF', {'previous_surface':prev,'current_surface':cur})
    assert diff['ok'] is True and diff['summary']['changed_row_count'] == 1
    q=run_options_lab_action('RUN_HRP_RMT_DIAGNOSTIC', {'prices_by_asset': {'A':[1,2,3,4], 'B':[1,1.5,2,3]}})
    assert q['ok'] is True and q['snapshot']['hrp']['ok'] is True
