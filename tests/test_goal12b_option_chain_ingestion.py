SAMPLE_CSV = """symbol,expiry,strike,right,bid,ask,spot,asof,source,iv
DEMO,2026-12-31,100,C,5,6,100,2026-06-15T00:00:00Z,unit_test,0.25
DEMO,2026-12-31,95,P,2,3,100,2026-06-15T00:00:00Z,unit_test,0.30
DEMO,2027-03-31,100,C,8,9,100,2026-06-15T00:00:00Z,unit_test,0.35
"""

from lib.options_chain_ingestion import build_option_chain_snapshot, parse_option_chain_csv_text
from lib.options_chain_normalizer import infer_option_chain_columns


def test_option_chain_csv_ingestion_normalizes_aliases():
    rows = parse_option_chain_csv_text(SAMPLE_CSV)
    mapping = infer_option_chain_columns(list(rows[0]))
    assert mapping["option_type"] == "right"
    assert mapping["underlying_price"] == "spot"
    snap = build_option_chain_snapshot(SAMPLE_CSV)
    assert snap["ok"] is True
    assert snap["rows"][0]["underlying"] == "DEMO"
    assert snap["rows"][0]["option_type"] == "call"
    assert snap["source_snapshot"]["used_for_calculation"] is True
