from lib.strategy_decision_log import STRATEGY_NOTICE, archive_strategy_commit, create_strategy_commit, list_strategy_commits


def test_strategy_decision_log(tmp_path):
    db=tmp_path/"sd.db"
    commit=create_strategy_commit(strategy_id="s", message="candidate requires review", db_path=db)
    assert "research records" in STRATEGY_NOTICE
    archive_strategy_commit(commit["commit_id"], db)
    assert list_strategy_commits(db_path=db) == []

