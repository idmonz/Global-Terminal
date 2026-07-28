from lib.research_report_sanitizer import escape_csv_formula_text, escape_report_identifier, sanitize_report_table_rows
from lib.options_chain_report_generator import build_options_chain_report


def test_goal12c_report_identifier_escaping_blocks_html_path_and_formula():
    assert '&lt;script' in escape_report_identifier('<script>alert(1)</script>')
    assert '[local-path-redacted]' in escape_report_identifier('/mnt/data/private/file.csv')
    assert escape_csv_formula_text('=cmd|bad').startswith('&#x27;')
    rows=sanitize_report_table_rows([{'source':'<b>x</b>', 'symbol':'=BAD'}])
    assert '&lt;b&gt;' in rows[0]['source']


def test_goal12c_chain_report_escapes_user_supplied_identifiers():
    chain={'rows':[{'underlying':'<script>x</script>','expiry':'2026-07-15','option_type':'call','strike':100,'bid':1,'ask':2,'underlying_price':100,'timestamp':'2026-06-15T00:00:00Z','source':'=bad'}], 'quality':{'accepted_rows':1,'rejected_rows':0,'caveated_rows':0}, 'source_snapshot':{'source':'/mnt/data/private/source.csv'}, 'freshness':{'freshness':'unknown'}, 'snapshot_id':'x'}
    report=build_options_chain_report(chain, include_iv=False)
    body=report['markdown_body']
    assert '<script>' not in body
    assert '[local-path-redacted]' in body
    assert '&#x27;=bad' in body
