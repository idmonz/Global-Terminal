from lib.options_book_scenario_report import build_option_book_stress_report


def test_goal12c_option_book_stress_report_builds_markdown():
    rows=[{'underlying':'SPY','option_type':'put','expiry':'2026-07-15','strike':100,'quantity':1,'position':'long','premium':4,'mark':5,'implied_volatility':0.2,'underlying_price':100,'time_to_expiry_years':0.2,'contract_multiplier':100,'source':'unit','timestamp':'x'}]
    report=build_option_book_stress_report(rows)
    assert report['ok'] is True
    assert report['report_type'] == 'options_book_stress_report'
    assert 'Stress Report' in report['markdown_body']
