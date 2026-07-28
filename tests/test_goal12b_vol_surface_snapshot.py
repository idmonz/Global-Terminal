SAMPLE_CSV = """symbol,expiry,strike,right,bid,ask,spot,asof,source,iv
DEMO,2026-12-31,100,C,5,6,100,2026-06-15T00:00:00Z,unit_test,0.25
DEMO,2026-12-31,95,P,2,3,100,2026-06-15T00:00:00Z,unit_test,0.30
DEMO,2027-03-31,100,C,8,9,100,2026-06-15T00:00:00Z,unit_test,0.35
"""

from lib.options_chain_ingestion import build_option_chain_snapshot
from lib.options_chain_iv import build_chain_iv_snapshot
from lib.options_vol_surface import build_smile_table, build_skew_table, build_term_structure_table, build_vol_surface_snapshot, interpolate_surface_grid_nearest_safe


def test_vol_surface_snapshot_and_tables_from_supplied_chain():
    iv = build_chain_iv_snapshot(build_option_chain_snapshot(SAMPLE_CSV))
    surface = build_vol_surface_snapshot(iv)
    assert surface["point_count"] == 3
    assert len(build_smile_table(surface)) == 3
    assert build_skew_table(surface)[0]["expiry"] == "2026-12-31"
    assert len(build_term_structure_table(surface)) == 2
    grid = interpolate_surface_grid_nearest_safe(surface, ["2026-12-31"], [97, 100])
    assert grid["grid"][0]["interpolated"] is True
