from pathlib import Path


def test_goal13a_license_audit_matrix_covers_required_sources():
    text = Path("docs/GOAL_13A_EXTERNAL_LICENSE_AUDIT.md").read_text(encoding="utf-8")
    for source in [
        "agent-skills-main.zip",
        "tensortrade-master.zip",
        "QuantDinger-main.zip",
        "Kronos-master.zip",
        "OpenAlice-master.zip",
        "worldmonitor-main.zip",
        "OpenBB-develop.zip",
        "worldview-main.zip",
    ]:
        assert source in text
    assert "Code copied" in text
    assert "No external source code" in text
    assert "NASA Open Source Agreement" in text


def test_goal13a_governance_docs_cite_primary_references():
    spec = Path("docs/GOAL_13A_SPEC.md").read_text(encoding="utf-8")
    for url in [
        "https://www.nist.gov/itl/ai-risk-management-framework",
        "https://airc.nist.gov/airmf-resources/airmf/",
        "https://arxiv.org/abs/1810.03993",
        "https://arxiv.org/abs/1803.09010",
        "https://mlflow.org/docs/latest/ml/model-registry/",
    ]:
        assert url in spec
