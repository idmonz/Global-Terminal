from lib.report_visuals import build_report_cards, build_report_timeline


def test_report_visuals():
    reports=[{"title":"B","generated_at":"2"},{"title":"A","generated_at":"1"}]
    assert build_report_cards(reports)[0]["title"] == "B"
    assert build_report_timeline(reports)[0]["title"] == "B"

