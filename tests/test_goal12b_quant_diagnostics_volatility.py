from lib.quant_diagnostics_volatility import build_volatility_diagnostics, ewma_volatility, volatility_clustering_score


def test_volatility_diagnostics_ewma_and_clustering():
    returns=[.01,-.02,.03,-.01,.01]
    assert len(ewma_volatility(returns)) == len(returns)
    assert volatility_clustering_score(returns) is not None
    assert "garch_placeholder_caveat" in build_volatility_diagnostics(returns)
