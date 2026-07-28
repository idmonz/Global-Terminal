from __future__ import annotations

from lib.compliance import contains_forbidden_language
from lib.strategy_registry import build_strategy_candidate_set, build_strategy_registry, validate_strategy_definition


def test_strategy_registry_returns_candidate_bundles_without_directive_language():
    registry = build_strategy_registry()
    assert len(registry) >= 15
    for definition in registry:
        ok, issues = validate_strategy_definition(definition)
        assert ok, issues
        assert not contains_forbidden_language(" ".join([definition["name"], definition["description"], definition["weighting_method"]]), allow_disclosure=False)

    candidates = build_strategy_candidate_set({"ticker list", "price history"})
    assert "is_available" in candidates.columns
    assert candidates["name"].str.contains("Equal Weight Baseline").any()
