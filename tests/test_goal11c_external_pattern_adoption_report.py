from pathlib import Path


def test_goal11c_external_pattern_adoption_report_exists_and_states_boundary():
    path = Path("docs/GOAL_11C_EXTERNAL_PATTERN_ADOPTION_REPORT.md")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    for required in ["external inventory", "files inspected", "concepts adopted", "concepts rejected", "license boundary", "source-copy boundary"]:
        assert required in text.lower()
    assert "no external source code was copied" in text.lower()
