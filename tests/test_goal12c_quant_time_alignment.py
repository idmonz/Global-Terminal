from lib.quant_diagnostics_time_alignment import align_series_by_timestamp


def test_goal12c_time_alignment_uses_timestamp_intersection():
    data={'A':[{'timestamp':'t1','value':1},{'timestamp':'t2','value':2}], 'B':[{'timestamp':'t2','value':3},{'timestamp':'t3','value':4}]}
    out=align_series_by_timestamp(data)
    assert out['ok'] is True
    assert out['timestamps'] == ['t2']
    assert out['aligned']['A'] == [2.0]


def test_goal12c_time_alignment_falls_back_to_latest_n_caveat():
    out=align_series_by_timestamp({'A':[1,2,3], 'B':[4,5,6]}, latest_n=2)
    assert out['alignment'] == 'latest_n_position'
    assert out['aligned']['A'] == [2.0,3.0]
