from lib.osint_report_context import build_osint_report_context


def test_osint_report_context():
    ctx=build_osint_report_context([{"title":"Red Sea"}], [{"display_name":"Red Sea","item_type":"chokepoint"}])
    assert ctx["match_count"] == 1

