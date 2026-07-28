from pathlib import Path


def test_goal11_governance_docs_exist():
    for name in ["GOAL_11_ENGINEERING_GOVERNANCE.md", "GOAL_11_SPEC.md", "GOAL_11_TASK_PLAN.md"]:
        text = (Path("docs")/name).read_text(encoding="utf-8")
        assert "Goal 11" in text or "GOAL_11" in text or "Goal 11" in name

