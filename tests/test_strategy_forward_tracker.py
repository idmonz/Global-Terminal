from lib.strategy_decision_log import create_strategy_commit
from lib.strategy_forward_tracker import build_forward_tracking_snapshot, update_forward_tracking


def test_strategy_forward_tracker(tmp_path):
    db=tmp_path/"ft.db"
    commit=create_strategy_commit(strategy_id="s", message="track candidate", db_path=db)
    assert build_forward_tracking_snapshot(commit)["research_only"] is True
    assert update_forward_tracking(commit["commit_id"], {"note":"observed"}, db)["commit_id"] == commit["commit_id"]

