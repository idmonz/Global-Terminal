SAMPLE_CSV = """symbol,expiry,strike,right,bid,ask,spot,asof,source,iv
DEMO,2026-12-31,100,C,5,6,100,2026-06-15T00:00:00Z,unit_test,0.25
DEMO,2026-12-31,95,P,2,3,100,2026-06-15T00:00:00Z,unit_test,0.30
DEMO,2027-03-31,100,C,8,9,100,2026-06-15T00:00:00Z,unit_test,0.35
"""

from datetime import datetime, timezone
from lib.options_chain_ingestion import build_option_chain_snapshot
from lib.options_chain_quality import label_option_chain_freshness, summarize_option_chain_quality


def test_option_chain_quality_labels_freshness_and_wide_spreads():
    fresh = label_option_chain_freshness("2026-06-15T00:00:00+00:00", now=datetime(2026,6,15,tzinfo=timezone.utc))
    assert fresh["freshness"] == "fresh"
    snap = build_option_chain_snapshot(SAMPLE_CSV)
    quality = summarize_option_chain_quality(snap)
    assert quality["accepted_rows"] == 3
    assert "supplied_csv_only" in quality["caveats"]
