import pytest

from lib.actionless_simulation_schema import (
    build_data_feed_snapshot,
    build_scenario_set,
    build_simulation_case_manifest,
    build_simulation_result_artifact,
    validate_safe_id,
)


def test_goal13a_schema_builds_research_only_case_and_datasheet():
    case = build_simulation_case_manifest(
        case_id="sim_case_1",
        title="Macro volatility scenario review",
        objective="Compare scenario diagnostics for local research.",
        linked_options_case_ids=["opt_case_1"],
        linked_strategy_commit_ids=["commit_abc123"],
        source_context={"local_path": "C:/Users/example/private.csv"},
    )
    assert case["case_id"] == "sim_case_1"
    assert case["actionless"] is True
    assert case["research_only"] is True
    assert "[local-path-redacted]" in str(case["source_context"])

    feed = build_data_feed_snapshot(
        feed_snapshot_id="feed_1",
        data_source_label="manual options surface snapshot",
        coverage={"assets": ["SPY"], "private_path": "/home/user/raw.csv"},
        fields=["underlying", "implied_volatility"],
        transformations=["winsorized stale rows for diagnostics"],
        missingness_notes=["No live provider required."],
    )
    assert feed["feed_snapshot_id"] == "feed_1"
    assert "[local-path-redacted]" in str(feed)


def test_goal13a_schema_blocks_unsafe_ids_and_action_language():
    with pytest.raises(ValueError):
        validate_safe_id("../escape", field_name="case_id")
    with pytest.raises(ValueError):
        build_simulation_case_manifest(
            case_id="bad_case",
            title="Directional case",
            objective="Execute order now",
        )
    with pytest.raises(ValueError):
        build_scenario_set(
            scenario_id="scenario_1",
            title="Buy now scenario",
            horizon="one month",
        )


def test_goal13a_result_artifact_is_diagnostic_only():
    result = build_simulation_result_artifact(
        result_id="result_1",
        scenario_id="scenario_1",
        model_artifact_id="model_1",
        input_snapshot_id="feed_1",
        metrics={"stress_loss_proxy": 0.12},
        warnings=["Diagnostic summary only."],
    )
    assert result["result_id"] == "result_1"
    assert result["status"] == "generated"
    assert result["research_only"] is True
