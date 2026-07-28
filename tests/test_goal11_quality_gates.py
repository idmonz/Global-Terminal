from pathlib import Path


def test_goal11_quality_gate_docs_exist():
    required = ["GOAL_11_PRE_FLIGHT_REPORT.md", "GOAL_11_EXTERNAL_REFERENCE_RESEARCH_REPORT.md", "GOAL_11_AGENT_SKILLS_RESEARCH_REPORT.md", "GOAL_11_ENGINEERING_GOVERNANCE.md", "GOAL_11_SPEC.md", "GOAL_11_TASK_PLAN.md"]
    for doc in required:
        assert (Path("docs") / doc).exists()

