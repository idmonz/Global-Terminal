from lib.quant_diagnostics_kalman import kalman_lite_level_trend


def test_goal12c_kalman_lite_builds_states():
    out=kalman_lite_level_trend([1,2,3,2,4])
    assert out['ok'] is True
    assert len(out['states']) == 5
    assert out['state_uncertainty_proxy'] >= 0


def test_goal12c_kalman_lite_requires_minimum_sample():
    assert kalman_lite_level_trend([1])['ok'] is False
