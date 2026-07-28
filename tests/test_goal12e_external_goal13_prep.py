from pathlib import Path


def test_goal12e_external_roadmap_and_goal13_prep_are_concrete():
    roadmap = Path("docs/EXTERNAL_REFERENCE_GOAL_BY_GOAL_ADOPTION_PLAN.md").read_text(encoding="utf-8")
    for token in ["tensortrade-master", "QuantDinger-main", "Kronos-master", "OpenAlice-master", "optlib-master", "agent-skills-main"]:
        assert token in roadmap
    assert "action-less simulation" in roadmap
    assert "prohibited-runtime" in roadmap
    assert "future-review-required only" not in roadmap
    prep = Path("docs/GOAL_13_ACTIONLESS_SIMULATION_ARCHITECTURE_PREP.md").read_text(encoding="utf-8")
    for token in ["simulation_case", "scenario_set", "data_feed_snapshot", "model_artifact", "simulation_result", "review_queue_item", "actionless_boundary"]:
        assert token in prep
    assert "no broker execution" in prep
