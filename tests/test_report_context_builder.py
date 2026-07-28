from lib.report_context_builder import build_report_context, build_report_source_snapshot


def test_report_context_builder(tmp_path):
    ctx=build_report_context("Watchlist Brief", tmp_path/"ctx.db")
    assert ctx["research_only"] is True
    assert build_report_source_snapshot(ctx)["freshness"] == "local"

