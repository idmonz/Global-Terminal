from lib.quant_diagnostics_returns import build_returns_diagnostics, log_returns, rolling_mean, rolling_volatility, simple_returns


def test_returns_diagnostics_are_deterministic():
    prices=[100, 101, 99, 102]
    assert len(simple_returns(prices)) == 3
    assert len(log_returns(prices)) == 3
    assert rolling_mean([1,2,3], 2)[0] is None
    assert rolling_volatility([.01,.02,.03], 2)[1] is not None
    assert build_returns_diagnostics(prices)["research_only"] is True
