from pathlib import Path
import pytest
from lib.options_chain_ingestion import read_option_chain_csv, build_option_chain_snapshot
from lib.options_chain_report_generator import build_options_chain_report, escape_report_value


def test_csv_path_traversal_rejected(tmp_path):
    safe=tmp_path/"safe"; safe.mkdir()
    outside=tmp_path/"outside.csv"; outside.write_text("symbol,expiry,strike,right,bid,ask,spot,asof\nX,2026-12-31,100,C,1,2,100,2026-06-15T00:00:00Z\n")
    with pytest.raises(ValueError):
        read_option_chain_csv(outside, allowed_root=safe)


def test_csv_formula_and_html_are_escaped_in_report():
    assert escape_report_value("=1+1").startswith("&#x27;=")
    csv="""symbol,expiry,strike,right,bid,ask,spot,asof,source\n<script>x</script>,2026-12-31,100,C,1,2,100,2026-06-15T00:00:00Z,=cmd\n"""
    snap=build_option_chain_snapshot(csv)
    body=build_options_chain_report(snap)["markdown_body"]
    assert "<script>" not in body
    assert "&lt;script&gt;" in body
    assert "outside.csv" not in body
