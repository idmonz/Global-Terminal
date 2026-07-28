SAMPLE_CSV = """symbol,expiry,strike,right,bid,ask,spot,asof,source,iv
DEMO,2026-12-31,100,C,5,6,100,2026-06-15T00:00:00Z,unit_test,0.25
DEMO,2026-12-31,95,P,2,3,100,2026-06-15T00:00:00Z,unit_test,0.30
DEMO,2027-03-31,100,C,8,9,100,2026-06-15T00:00:00Z,unit_test,0.35
"""

from lib.options_chain_report_generator import build_options_chain_report, escape_report_value, generate_options_chain_report
from lib.options_surface_report_generator import generate_options_surface_report
from lib.options_book_report_generator import generate_options_book_risk_report
from lib.options_chain_ingestion import build_option_chain_snapshot
from lib.options_chain_iv import build_chain_iv_snapshot
from lib.quant_diagnostics_report import build_quant_diagnostics_report


def test_goal12b_reports_are_generated_with_disclosure():
    chain=build_option_chain_snapshot(SAMPLE_CSV)
    report=build_options_chain_report(chain)
    assert "research calculations only" in report["markdown_body"]
    assert "&#x27;=cmd" == escape_report_value("=cmd")
    assert generate_options_chain_report(SAMPLE_CSV)["ok"] is True
    assert generate_options_surface_report(build_chain_iv_snapshot(chain))["ok"] is True
    book = generate_options_book_risk_report([{"underlying":"DEMO","option_type":"call","expiry":"2026-12-31","strike":100,"quantity":1,"position":"long","premium":5,"mark":6,"implied_volatility":0.2,"underlying_price":100}])
    assert book["report_type"] == "options_book_risk_report"
    assert build_quant_diagnostics_report({"A":[100,101,99,102],"B":[50,51,49,52]})["ok"] is True
