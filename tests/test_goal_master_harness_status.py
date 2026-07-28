from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SKILLS = {
    "global-terminal-preflight",
    "global-terminal-product-parity",
    "global-terminal-frontend-visual-qa",
    "global-terminal-release-gate",
    "global-terminal-cleanroom-reference",
    "global-terminal-next-goal-writer",
}


def test_goal_master_harness_files_are_present_and_non_placeholder():
    required_docs = {
        "AGENTS.md",
        "apps/web/AGENTS.md",
        "docs/CODEX_WORKFLOW.md",
        "docs/CODEX_REVIEW_CHECKLIST.md",
        "docs/GOAL_MASTER_PRODUCT_PARITY_STATUS.md",
        "docs/GOAL_MASTER_HARNESS_STATUS.md",
        "docs/GOAL_MASTER_ACTIVE_PHASE_DECISION.md",
        "docs/GOAL_MASTER_BENCHMARK_SCORECARD.md",
    }

    for relative in required_docs:
        path = ROOT / relative
        assert path.exists(), relative
        text = path.read_text(encoding="utf-8")
        assert len(text.strip()) > 80, relative
        assert "TODO" not in text, relative


def test_repo_skills_have_minimal_valid_frontmatter_and_workflows():
    for skill_name in REQUIRED_SKILLS:
        skill_path = ROOT / ".agents" / "skills" / skill_name / "SKILL.md"
        assert skill_path.exists(), skill_name
        text = skill_path.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert f"name: {skill_name}" in text
        assert "description:" in text
        assert "## Workflow" in text
        assert "TODO" not in text

