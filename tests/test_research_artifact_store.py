from lib.research_artifact_store import list_research_artifacts, store_research_artifact


def test_research_artifact_store(tmp_path):
    db=tmp_path/"art.db"
    art=store_research_artifact("c1", "report_snapshot", "Report", payload={"x":1}, db_path=db)
    assert list_research_artifacts("c1", db)[0]["artifact_id"] == art["artifact_id"]

