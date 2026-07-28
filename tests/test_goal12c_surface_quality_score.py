from lib.options_surface_quality import build_surface_quality_score, build_surface_anomaly_table


def test_goal12c_surface_quality_scores_sparse_and_model_mix():
    surface={'points':[{'expiry':'e1','strike':100.0,'option_type':'call','mid_iv':0.2,'pricing_model':'black_scholes','freshness':'unknown','interpolated':False},{'expiry':'e1','strike':110.0,'option_type':'call','mid_iv':0.3,'pricing_model':'black_76','freshness':'user_supplied','interpolated':True}]}
    q=build_surface_quality_score(surface)
    assert q['ok'] is True
    assert q['score'] < 100
    assert 'sparse_surface_caveat' in q['caveats']
    assert 'model_mix_caveat' in q['caveats']
    assert isinstance(build_surface_anomaly_table(surface), list)
