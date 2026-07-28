from lib.report_renderer import render_report_markdown, render_report_html


def test_report_renderer():
    md=render_report_markdown({"report_type":"Watchlist Brief","watchlist":{"summary":{"count":0}},"alert_events":[],"strategy_commits":[],"provider_gaps":[]})
    assert "Source Snapshot" in md
    assert render_report_html({"report_type":"Watchlist Brief"}).startswith("<article>")

