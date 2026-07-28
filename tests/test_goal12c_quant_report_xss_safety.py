from lib.quant_diagnostics_report import build_quant_diagnostics_report


def test_goal12c_quant_report_escapes_asset_names():
    report=build_quant_diagnostics_report({'<script>BAD</script>':[1,2,3,4], 'B':[1,1.1,1.2,1.3]})
    assert '<script>' not in report['markdown_body']
    assert '&lt;script&gt;' in report['markdown_body']
