SAMPLE_CSV = """symbol,expiry,strike,right,bid,ask,spot,asof,source,iv,asset_class
DEMO,2026-12-31,100,C,5,6,100,2026-06-15T00:00:00Z,unit_test,0.25,equity
DEMO,2026-12-31,95,P,2,3,100,2026-06-15T00:00:00Z,unit_test,0.30,equity
DEMO,2027-03-31,100,C,8,9,100,2026-06-15T00:00:00Z,unit_test,0.35,equity
"""

from lib.options_chain_ingestion import build_option_chain_snapshot
from lib.options_chain_iv import build_chain_iv_snapshot, compute_mid_price, compute_bid_ask_spread, identify_no_arbitrage_violations


def test_chain_iv_diagnostics_solve_mid_iv_and_caveat_invalid_prices():
    snap = build_option_chain_snapshot(SAMPLE_CSV)
    iv = build_chain_iv_snapshot(snap, default_tte_years=30/365)
    assert iv["solved_count"] >= 2
    assert iv["rows"][0]["mid_iv"] is not None
    assert compute_mid_price(7, 6)["ok"] is False
    assert compute_bid_ask_spread(7, 6)["reason"] == "invalid_or_crossed_bid_ask"
    bad = {"option_type":"call","underlying_price":100,"strike":10,"time_to_expiry_years":30/365,"risk_free_rate":0,"mid":1}
    assert "premium_below_intrinsic_or_discount_bound" in identify_no_arbitrage_violations(bad, 1)
