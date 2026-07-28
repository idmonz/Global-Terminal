from lib.options_chain_ingestion import build_option_chain_snapshot
from lib.options_chain_iv import build_chain_iv_snapshot


def test_goal12c_chain_iv_uses_derived_tte_and_row_model():
    rows=[{'underlying':'CL','asset_class':'futures','expiry':'2026-07-15','strike':70,'option_type':'call','bid':2.1,'ask':2.4,'underlying_price':70,'futures_price':70,'timestamp':'2026-06-15T00:00:00Z','source':'unit','risk_free_rate':0.04}]
    snap={'snapshot_id':'manual','rows':rows,'source_snapshot':{'source':'unit'}}
    iv=build_chain_iv_snapshot(snap)
    row=iv['rows'][0]
    assert row['tte_status'] == 'derived'
    assert row['pricing_model'] == 'black_76'
    assert row['mid_iv'] is not None


def test_goal12c_chain_iv_does_not_fake_missing_tte():
    rows=[{'underlying':'SPY','asset_class':'equity','expiry':'2026-07-15','strike':100,'option_type':'call','bid':1,'ask':2,'underlying_price':100,'source':'unit'}]
    snap={'snapshot_id':'manual','rows':rows,'source_snapshot':{'source':'unit'}}
    iv=build_chain_iv_snapshot(snap)
    row=iv['rows'][0]
    assert row['mid_iv'] is None
    assert row['tte_status'] == 'missing_timestamp'
