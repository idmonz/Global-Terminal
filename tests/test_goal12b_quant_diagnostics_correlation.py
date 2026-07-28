from lib.quant_diagnostics_correlation import build_correlation_diagnostics, correlation_matrix, eigenvalue_summary, rmt_noise_threshold_caveat


def test_correlation_diagnostics_matrix_and_eigenvalues():
    corr = correlation_matrix({"A":[.01,.02,.03], "B":[.01,.01,.02]})
    assert corr["ok"] is True
    eig = eigenvalue_summary(corr)
    assert len(eig["eigenvalues"]) == 2
    assert rmt_noise_threshold_caveat(2, 10)["threshold_concept"] is not None
    assert build_correlation_diagnostics({"A":[.01,.02,.03], "B":[.01,.01,.02]})["ok"] is True
