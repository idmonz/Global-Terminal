from pathlib import Path


GOAL13A_MODULES = [
    Path("lib/actionless_simulation_schema.py"),
    Path("lib/actionless_simulation_store.py"),
    Path("lib/actionless_simulation_index.py"),
    Path("lib/actionless_simulation_workflow.py"),
    Path("lib/model_artifact_governance.py"),
]


def test_goal13a_no_external_runtime_imports_or_heavy_dependencies():
    req = Path("requirements.txt").read_text(encoding="utf-8").lower()
    for forbidden in ["tensortrade", "kronos", "torch", "tensorflow", "huggingface", "openbb"]:
        assert forbidden not in req

    combined = "\n".join(path.read_text(encoding="utf-8") for path in GOAL13A_MODULES)
    for forbidden_import in ["import tensortrade", "import kronos", "import openbb", "from tensortrade", "from kronos", "from openbb"]:
        assert forbidden_import not in combined.lower()


def test_goal13a_external_boundary_docs_record_no_source_copy():
    docs = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in [
            "docs/GOAL_13A_EXTERNAL_REFERENCE_RESEARCH_REPORT.md",
            "docs/GOAL_13A_EXTERNAL_LICENSE_AUDIT.md",
        ]
    )
    assert "No external source code was copied" in docs
    assert "AGPL" in docs
    assert "behavior-only" in docs
    assert "No model runtime" in docs or "No weights" in docs
