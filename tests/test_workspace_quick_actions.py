from lib.workspace_quick_actions import build_quick_actions, run_quick_action


def test_workspace_quick_actions(tmp_path):
    db=tmp_path/"qa.db"
    assert build_quick_actions()
    assert run_quick_action("ADD WATCHLIST", {"symbol":"BTCUSDT"}, db)["result"]["symbol"] == "BTCUSDT"
    assert run_quick_action("EVALUATE ALERTS", {}, db)["result"] == []

