from lib.quant_diagnostics_mean_reversion import build_mean_reversion_diagnostics, hurst_exponent, ou_half_life


def test_goal12c_hurst_ou_return_caveats_for_small_samples():
    assert hurst_exponent([1,2,3]) is None
    assert ou_half_life([1,1,1]) is None
    out=build_mean_reversion_diagnostics([1,2,3])
    assert out['ok'] is True
    assert 'stationarity_caveat' in out
