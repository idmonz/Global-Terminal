from pathlib import Path


def test_goal12e_no_external_source_trees_or_runtime_imports():
    for name in ["external", "agent-skills-main", "optlib-master", "Kronos-master", "tensortrade-master", "QuantDinger-main", "OpenAlice-master"]:
        assert not Path(name).exists()
    for py in Path("lib").glob("*.py"):
        text = py.read_text(encoding="utf-8")
        assert "import optlib" not in text
        assert "from optlib" not in text
        assert "tensorflow" not in text.lower()
        assert "huggingface" not in text.lower() or "caveat" in text.lower() or "placeholder" in text.lower()
