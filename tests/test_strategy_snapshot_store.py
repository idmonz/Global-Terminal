from lib.strategy_snapshot_store import build_strategy_snapshot, create_strategy_commit, list_strategy_commits


def test_strategy_snapshot_store(tmp_path):
    db=tmp_path/"ss.db"
    snap=build_strategy_snapshot({"name":"candidate"})
    assert snap["research_only"] is True
    create_strategy_commit(strategy_id="s1", message="research commit", db_path=db)
    assert list_strategy_commits(db_path=db)

