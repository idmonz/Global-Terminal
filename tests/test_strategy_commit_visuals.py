from lib.strategy_commit_visuals import build_strategy_commit_cards


def test_strategy_commit_visuals():
    cards=build_strategy_commit_cards([{"commit_id":"c","strategy_id":"s","status":"draft","guard_results_json":[]}])
    assert cards[0]["commit_id"] == "c"

