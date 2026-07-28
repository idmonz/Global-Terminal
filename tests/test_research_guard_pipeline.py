from lib.research_guard_pipeline import no_recommendation_language_guard, run_research_guard_pipeline, summarize_guard_results, build_guard_cards


def test_guard_pipeline_detects_actionable_phrase():
    result=no_recommendation_language_guard("trade now")
    assert result["status"] == "warning"
    results=run_research_guard_pipeline({"data_quality":{"score":0.5}}, text="research candidate")
    assert summarize_guard_results(results)["requires_review"] is True
    assert build_guard_cards(results)

