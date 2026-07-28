from lib.options_lab_page_layout import build_options_lab_page_payload


def test_goal12c_options_lab_payload_has_new_sections_and_chips():
    payload=build_options_lab_page_payload({'option_type':'call','underlying_price':100,'strike':100,'time_to_expiry_years':0.5,'risk_free_rate':0.03,'volatility':0.2,'premium':6,'model':'black_scholes'}, chain_rows=[{'underlying':'SPY','asset_class':'equity','expiry':'2026-07-15','strike':100,'option_type':'call','bid':6,'ask':7,'underlying_price':100,'timestamp':'2026-06-15T00:00:00Z','source':'unit'}])
    assert 'Surface QA' in payload['sections']
    assert payload['source_chips']['chain'] == 'user_supplied'
    assert payload['surface_qa'] is not None
