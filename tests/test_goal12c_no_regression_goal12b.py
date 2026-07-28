from lib.options_chain_ingestion import build_option_chain_snapshot
from lib.options_vol_surface import build_vol_surface_snapshot
from lib.options_chain_iv import build_chain_iv_snapshot
from lib.options_book_risk import build_option_book_risk_snapshot


def test_goal12c_preserves_goal12b_chain_surface_book_public_apis():
    rows=[{'underlying':'SPY','asset_class':'equity','expiry':'2026-07-15','strike':100,'option_type':'call','bid':5,'ask':6,'underlying_price':100,'timestamp':'2026-06-15T00:00:00Z','source':'unit'}]
    chain=build_option_chain_snapshot(rows=rows)
    iv=build_chain_iv_snapshot(chain)
    surface=build_vol_surface_snapshot(iv)
    book=build_option_book_risk_snapshot([{'underlying':'SPY','option_type':'call','expiry':'2026-07-15','strike':100,'quantity':1,'position':'long','premium':5,'mark':6,'implied_volatility':0.2,'underlying_price':100,'contract_multiplier':100,'source':'unit','timestamp':'x'}])
    assert chain['ok'] is True
    assert iv['ok'] is True
    assert surface['ok'] is True
    assert 'totals' in book
