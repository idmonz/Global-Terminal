from lib.quant_diagnostics_rmt import build_rmt_diagnostic, eigenvalue_noise_threshold


def test_goal12c_rmt_diagnostic_returns_threshold_and_eigenvalues():
    out=build_rmt_diagnostic({'A':[0.01,0.02,-0.01,0.00], 'B':[0.02,0.01,0.00,-0.01]})
    assert out['ok'] is True
    assert out['threshold']['lambda_plus'] is not None
    assert out['eigenvalues']


def test_goal12c_rmt_threshold_handles_bad_sizes():
    assert eigenvalue_noise_threshold(0, 0)['ok'] is False
