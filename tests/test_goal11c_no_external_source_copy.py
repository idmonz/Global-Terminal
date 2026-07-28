from pathlib import Path


def test_goal11c_runtime_does_not_reference_external_source_trees():
    runtime = list(Path("lib").glob("*.py")) + list(Path("pages").glob("*.py"))
    forbidden = ["OpenStock-main", "worldmonitor-main", "OpenAlice-master", "BB-Terminal-main", "bloomberg-terminal-main", "osiris-master", "agent-skills-main"]
    for path in runtime:
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path
