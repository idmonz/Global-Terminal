from lib.quant_diagnostics_hrp import build_hrp_diagnostic


def test_goal12c_hrp_diagnostic_builds_risk_tree_without_allocation_claim():
    out=build_hrp_diagnostic({'A':[0.01,0.02,-0.01], 'B':[0.02,0.01,0.00]})
    assert out['ok'] is True
    assert out['risk_tree'][0]['cluster'] == 'root'
    assert abs(sum(out['inverse_vol']['inverse_vol_weights_diagnostic'].values()) - 1.0) < 1e-9
