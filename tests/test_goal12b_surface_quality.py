SAMPLE_CSV = """symbol,expiry,strike,right,bid,ask,spot,asof,source,iv
DEMO,2026-12-31,100,C,5,6,100,2026-06-15T00:00:00Z,unit_test,0.25
DEMO,2026-12-31,95,P,2,3,100,2026-06-15T00:00:00Z,unit_test,0.30
DEMO,2027-03-31,100,C,8,9,100,2026-06-15T00:00:00Z,unit_test,0.35
"""

from lib.options_chain_ingestion import build_option_chain_snapshot
from lib.options_chain_iv import build_chain_iv_snapshot
from lib.options_vol_surface import build_vol_surface_snapshot, summarize_surface_quality
from lib.options_surface_visuals import build_options_surface_visual_payload


def test_surface_quality_and_visual_payload_are_research_labeled():
    surface = build_vol_surface_snapshot(build_chain_iv_snapshot(build_option_chain_snapshot(SAMPLE_CSV)))
    quality = summarize_surface_quality(surface)
    assert quality["expiry_count"] == 2
    visual = build_options_surface_visual_payload(surface)
    assert visual["research_only"] is True
    assert visual["chart_type"] == "heatmap"
