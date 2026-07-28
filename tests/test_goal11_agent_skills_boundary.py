from pathlib import Path
from scripts.build_release_zip import iter_release_files


def test_agent_skills_reference_only_and_excluded():
    report = Path("docs/GOAL_11_AGENT_SKILLS_RESEARCH_REPORT.md")
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "No runtime files" in text or "No runtime" in text
    names = [p.as_posix() for p in iter_release_files()]
    assert not any("agent-skills-main" in name or ".claude-plugin" in name or "hooks/hooks.json" in name for name in names)

