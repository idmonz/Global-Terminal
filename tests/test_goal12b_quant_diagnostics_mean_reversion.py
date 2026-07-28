from lib.quant_diagnostics_mean_reversion import build_mean_reversion_diagnostics, hurst_exponent, ou_half_life, pair_residual_diagnostic


def test_mean_reversion_diagnostics_return_caveated_payloads():
    series=[100,101,99,100,101,99,100,100,101,99,100,101,99,100,100,101,99,100,101,99,100,100,101]
    assert hurst_exponent(series) is not None
    assert build_mean_reversion_diagnostics(series)["stationarity_caveat"]
    assert pair_residual_diagnostic(series, [x*1.01 for x in series])["ok"] is True
    # Half-life may be None for non-mean-reverting samples but must be safe.
    assert ou_half_life(series) is None or ou_half_life(series) > 0
