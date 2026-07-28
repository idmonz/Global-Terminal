from pathlib import Path


def test_no_external_source_trees_copied_into_runtime():
    runtime = list(Path("lib").glob("*.py")) + list(Path("pages").glob("*.py"))
    forbidden = ["OpenStock-main", "worldmonitor-main", "OpenAlice-master", "BB-Terminal-main", "bloomberg-terminal-main", "agent-skills-main"]
    for path in runtime:
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden)

