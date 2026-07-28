from lib.report_inbox import create_report, get_report
from lib.report_reader_workflow import build_report_reader_workflow_state, update_selected_report_review


def test_goal11d_report_reader_selects_second_and_filters(tmp_path):
    db = tmp_path / "workspace.db"
    first = create_report(report_type="watchlist", title="First report", summary="one", html_body_optional="<b>one</b>", db_path=db)
    second = create_report(report_type="provider", title="Second report", summary="two", provider_gaps=["missing-key"], html_body_optional="<script>x</script>", db_path=db)
    state = build_report_reader_workflow_state(selected_report_id=second["report_id"], db_path=db)
    assert state["reader"]["title"] == "Second report"
    assert "&lt;script&gt;" in state["export_payload"]["html_preview_safe"]
    assert state["source_caveat_panel"]["gaps"] == ["missing-key"]

    provider_state = build_report_reader_workflow_state(report_type="provider", db_path=db)
    assert len(provider_state["sidebar"]["items"]) == 1
    update = update_selected_report_review(second["report_id"], "requires_review", notes="needs source check", db_path=db)
    assert update["ok"] is True
    assert get_report(second["report_id"], db)["report_review_status"] == "requires_review"
    status_state = build_report_reader_workflow_state(review_status="requires_review", db_path=db)
    assert status_state["sidebar"]["items"][0]["report_id"] == second["report_id"]
