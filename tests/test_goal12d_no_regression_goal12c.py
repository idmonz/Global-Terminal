from lib.options_time_to_expiry import derive_time_to_expiry_years
from lib.options_surface_diff import build_surface_snapshot_diff
from lib.quant_diagnostics_hrp import build_hrp_diagnostic
from lib.quant_diagnostics_rmt import build_rmt_diagnostic
from lib.quant_diagnostics_kalman import kalman_lite_level_trend
from lib.quant_diagnostics_garch_lite import garch_lite_diagnostic


def test_goal12d_goal12c_public_apis_still_available():
    assert derive_time_to_expiry_years({'expiry':'2026-07-15','timestamp':'2026-06-15'})['ok'] is True
    assert build_surface_snapshot_diff({'points':[]}, {'points':[]})['ok'] is True
    returns = {'A':[0.01, -0.01, 0.02, 0.0], 'B':[0.0, 0.01, -0.01, 0.02]}
    assert build_hrp_diagnostic(returns)['ok'] is True
    assert build_rmt_diagnostic(returns)['ok'] is True
    assert kalman_lite_level_trend([1,2,3,4])['ok'] is True
    assert garch_lite_diagnostic([0.01,-0.02,0.01,0.0])['ok'] is True
