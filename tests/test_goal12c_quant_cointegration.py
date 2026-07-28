from lib.quant_diagnostics_cointegration import cointegration_diagnostic


def test_goal12c_cointegration_has_fallback_or_optional_statsmodels():
    out=cointegration_diagnostic([1,2,3,4,5,6], [1,2,2.9,4.1,5.1,6.2])
    assert out['ok'] is True
    assert 'statsmodels_available' in out
    assert 'pvalue_caveat' in out
