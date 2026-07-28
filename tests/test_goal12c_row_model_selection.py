from lib.options_model_selector import infer_option_pricing_model_for_row, build_row_pricing_input


def test_goal12c_futures_row_selects_black_76():
    row={'asset_class':'futures','futures_price':70,'underlying_price':70,'strike':70,'option_type':'call','time_to_expiry_years':0.5}
    assert infer_option_pricing_model_for_row(row)['model'] == 'black_76'
    assert build_row_pricing_input(row)['model'] == 'black_76'


def test_goal12c_fx_row_selects_garman_kohlhagen():
    row={'asset_class':'fx','underlying_price':1.1,'strike':1.1,'option_type':'put','time_to_expiry_years':0.5,'domestic_rate':0.05,'foreign_rate':0.02}
    assert infer_option_pricing_model_for_row(row)['model'] == 'garman_kohlhagen'
    inp=build_row_pricing_input(row)
    assert inp['domestic_rate'] == 0.05 and inp['foreign_rate'] == 0.02


def test_goal12c_equity_crypto_and_unknown_model_caveats():
    assert infer_option_pricing_model_for_row({'asset_class':'equity'})['model'] == 'black_scholes'
    crypto = infer_option_pricing_model_for_row({'asset_class':'crypto'})
    assert crypto['model'] == 'black_scholes' and crypto['caveats']
    unknown = infer_option_pricing_model_for_row({'asset_class':'mystery'})
    assert unknown['ok'] is False and unknown['caveats']
