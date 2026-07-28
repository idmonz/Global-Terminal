from lib.quant_diagnostics_garch_lite import garch_lite_diagnostic


def test_goal12c_garch_lite_returns_clustering_payload():
    out=garch_lite_diagnostic([0.01,-0.02,0.03,-0.01,0.02])
    assert out['ok'] is True
    assert 'ewma_last' in out
    assert 'squared_return_clustering' in out
