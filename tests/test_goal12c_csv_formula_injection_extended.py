from lib.research_report_sanitizer import escape_csv_formula_text


def test_goal12c_csv_formula_injection_prefixes_are_escaped():
    for value in ['=1+1', '+SUM(A1:A2)', '-cmd', '@HYPERLINK']:
        assert escape_csv_formula_text(value).startswith('&#x27;')
