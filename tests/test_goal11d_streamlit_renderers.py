from lib.streamlit_research_renderers import (
    render_action_cards,
    render_chip_strip,
    render_command_result_cards,
    render_empty_state,
    render_intel_feed,
    render_live_alerts_panel,
    render_report_reader,
    render_report_sidebar,
    render_strategy_review_queue,
    render_tool_cards,
)


def test_goal11d_renderers_are_import_safe_without_streamlit():
    assert render_chip_strip([{"label": "fresh"}])["component"] == "chip_strip"
    assert render_action_cards([{"title": "A"}])["research_only"] is True
    assert render_command_result_cards([{"title": "C"}])["component"] == "command_result_cards"
    assert render_report_sidebar({"items": [], "selected_report_id": ""})["component"] == "report_sidebar"
    assert render_report_reader({"title": "<script>", "safe_preview": "safe"})["safe_by_default"] is True
    assert render_strategy_review_queue([])["component"] == "strategy_review_queue"
    assert render_intel_feed({"rows": []})["component"] == "intel_feed"
    assert render_live_alerts_panel({"empty_message": "none"})["component"] == "live_alerts_panel"
    assert render_tool_cards({"tools": []})["component"] == "tool_cards"
    assert render_empty_state("none")["component"] == "empty_state"
