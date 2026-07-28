from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase6j_agent_harness_has_one_active_plan_and_short_map():
    active = list((ROOT / "docs" / "exec-plans" / "active").glob("*.md"))
    assert len(active) == 1
    assert active[0].name.startswith("PHASE_")
    assert "Status:" in active[0].read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert len(agents.encode("utf-8")) < 12_000
    assert "docs/PLANS.md" in agents
    assert "validate_agent_harness.py" in agents


def test_phase6j_required_harness_documents_exist():
    for relative in (
        "docs/PLANS.md",
        "docs/SECURITY.md",
        "docs/ROADMAP.md",
        "docs/NEXT_ROADMAP_EXECUTION_PROMPT.md",
        "docs/GOAL_MASTER_ACTIVE_PHASE_DECISION.md",
        "docs/exec-plans/completed/PHASE_6J.md",
    ):
        assert (ROOT / relative).is_file(), relative


def test_phase6j_harness_validator_passes():
    from scripts.validate_agent_harness import validate_harness

    report = validate_harness(ROOT)
    assert report["ok"] is True
    assert report["active_plan_count"] == 1
