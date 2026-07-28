from pathlib import Path


def test_external_reference_report_exists_and_no_runtime_external_imports():
    report = Path("docs/GOAL_11_EXTERNAL_REFERENCE_RESEARCH_REPORT.md")
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "No external source code was copied" in text
    for py in Path("lib").glob("*.py"):
        if py.name.startswith("research_") or "watchlist" in py.name or "workspace" in py.name or "report" in py.name or "strategy" in py.name or "alert" in py.name:
            body = py.read_text(encoding="utf-8")
            assert "external/" not in body
            assert "OpenStock-main" not in body
            assert "agent-skills-main" not in body

