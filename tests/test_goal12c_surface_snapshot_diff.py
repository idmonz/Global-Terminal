from lib.options_surface_diff import build_surface_snapshot_diff, build_surface_change_summary


def test_goal12c_surface_snapshot_diff_detects_changes_and_missing():
    prev={'points':[{'expiry':'e1','strike':100.0,'option_type':'call','mid_iv':0.2,'moneyness':1.0},{'expiry':'e1','strike':110.0,'option_type':'call','mid_iv':0.25,'moneyness':1.1}]}
    cur={'points':[{'expiry':'e1','strike':100.0,'option_type':'call','mid_iv':0.3,'moneyness':1.0},{'expiry':'e2','strike':100.0,'option_type':'put','mid_iv':0.4,'moneyness':1.0}]}
    diff=build_surface_snapshot_diff(prev, cur)
    summary=build_surface_change_summary(diff)
    assert len(diff['changed_rows']) == 1
    assert summary['new_row_count'] == 1
    assert summary['missing_row_count'] == 1
