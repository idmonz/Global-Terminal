from lib.strategy_commit_engine import create_strategy_commit, get_strategy_commit, compare_strategy_commits, attach_report_to_commit, attach_watchlist_items_to_commit


def test_strategy_commit_engine(tmp_path):
    db=tmp_path/"sc.db"
    a=create_strategy_commit(strategy_id="s", message="first", db_path=db)
    b=create_strategy_commit(strategy_id="s", message="second", parent_commit_id=a["commit_id"], db_path=db)
    assert get_strategy_commit(a["commit_id"], db)
    assert compare_strategy_commits(a["commit_id"], b["commit_id"], db)["same_strategy"] is True
    assert attach_report_to_commit(a["commit_id"], "r1", db)["linked_reports"] == ["r1"]
    assert attach_watchlist_items_to_commit(a["commit_id"], ["w1"], db)["linked_watchlist_items"] == ["w1"]

