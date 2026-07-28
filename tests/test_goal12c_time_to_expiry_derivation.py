from lib.options_time_to_expiry import derive_time_to_expiry_years, derive_days_to_expiry


def test_goal12c_tte_derives_from_expiry_and_timestamp():
    out = derive_time_to_expiry_years({'expiry': '2026-07-15', 'timestamp': '2026-06-15T00:00:00Z'})
    assert out['ok'] is True
    assert 29.9 < out['days_to_expiry'] < 30.1
    assert 0.08 < out['time_to_expiry_years'] < 0.083


def test_goal12c_missing_timestamp_is_caveated_not_faked():
    out = derive_time_to_expiry_years({'expiry': '2026-07-15'})
    assert out['ok'] is False
    assert out['time_to_expiry_years'] is None
    assert out['status'] == 'missing_timestamp'


def test_goal12c_expired_option_is_caveated():
    out = derive_days_to_expiry('2026-06-01', '2026-06-15T00:00:00Z')
    assert out['ok'] is False
    assert out['status'] == 'expired'
