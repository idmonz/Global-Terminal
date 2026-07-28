from lib.strategy_decision_log import create_strategy_commit, compare_strategy_commits, build_strategy_commit_graph_payload, attach_watchlist_items_to_commit, attach_report_to_commit
from lib.research_guard_pipeline import run_research_guard_pipeline, summarize_guard_results


def test_guard_pipeline_warns_on_thin_sample_proxy_stale_and_leverage():
    results = run_research_guard_pipeline({"data_quality": {"status": "proxy", "score": 40, "proxy_ratio": 0.5, "freshness": "stale"}, "backtest": {"sample_size": 30, "max_drawdown": -30}, "risk": {"leverage": 3}})
    summary = summarize_guard_results(results)
    assert summary["requires_review"] is True
    statuses = {r["guard"]: r["status"] for r in results}
    assert statuses["sample_length_guard"] == "warning"
    assert statuses["proxy_dependence_guard"] == "warning"
    assert statuses["source_freshness_guard"] == "warning"
    assert statuses["leverage_guard"] == "warning"


def test_commit_diff_and_graph_detect_changed_snapshots(tmp_path):
    db = tmp_path / "research.db"
    c1 = create_strategy_commit(strategy_id="s1", message="Initial research record", strategy_config_snapshot={"lookback": 20}, db_path=db)
    c2 = create_strategy_commit(strategy_id="s1", parent_commit_id=c1["commit_id"], message="Updated research record", strategy_config_snapshot={"lookback": 50}, oos_snapshot={"score": 0.2}, db_path=db)
    diff = compare_strategy_commits(c1["commit_id"], c2["commit_id"], db)
    assert "strategy_config_snapshot_json" in diff["changed_fields"]
    graph = build_strategy_commit_graph_payload(db_path=db)
    assert graph["commit_count"] == 2
    assert graph["edges"][0]["source"] == c1["commit_id"]


def test_commit_attachments_persist(tmp_path):
    db = tmp_path / "research.db"
    commit = create_strategy_commit(strategy_id="s2", message="Attach records", db_path=db)
    assert "r1" in attach_report_to_commit(commit["commit_id"], "r1", db)["linked_reports"]
    assert "w1" in attach_watchlist_items_to_commit(commit["commit_id"], ["w1"], db)["linked_watchlist_items"]
