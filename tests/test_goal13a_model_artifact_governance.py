import pytest

from lib.model_artifact_governance import (
    build_external_model_placeholder_cards,
    build_model_artifact_card,
    build_model_artifact_registry_summary,
)


def test_goal13a_model_artifact_card_contains_governance_fields():
    card = build_model_artifact_card(
        model_artifact_id="model_card_1",
        model_name="Local Volatility Diagnostic Card",
        category="volatility_model",
        version="v1",
        lifecycle_status="approved_for_research",
        intended_use="Research-only volatility diagnostics.",
        output_type="diagnostic",
        evaluation_summary="Deterministic summary from supplied case inputs.",
        lineage={"case_id": "sim_case_1", "private_path": "/mnt/data/private.json"},
        aliases=["local_vol_diag"],
        tags=["goal13a", "metadata_only"],
    )
    assert card["model_artifact_id"] == "model_card_1"
    assert card["metadata_only"] is True
    assert card["no_runtime"] is True
    assert card["review_status"] == "new"
    assert "[local-path-redacted]" in str(card["lineage"])


def test_goal13a_model_artifact_blocks_model_file_paths():
    with pytest.raises(ValueError):
        build_model_artifact_card(
            model_artifact_id="unsafe_model",
            model_name="Unsafe Model",
            artifact_uri="C:/Users/me/model.pt",
        )


def test_goal13a_external_model_placeholders_are_metadata_only():
    cards = build_external_model_placeholder_cards()
    ids = {card["model_artifact_id"] for card in cards}
    assert {"kronos_metadata_placeholder", "tensortrade_actionless_placeholder", "quantdinger_review_placeholder"} <= ids
    assert all(card["metadata_only"] and card["no_runtime"] for card in cards)
    summary = build_model_artifact_registry_summary(cards)
    assert summary["model_artifact_count"] == len(cards)
    assert summary["no_runtime"] is True
