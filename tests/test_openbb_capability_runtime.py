from __future__ import annotations

import types

from lib.openbb_capability_runtime import build_openbb_endpoint_gap_table, build_runtime_capability_matrix, detect_openbb_runtime_capabilities


def test_runtime_capability_matrix_supports_mock_root():
    root = types.SimpleNamespace(equity=types.SimpleNamespace(profile=lambda **kwargs: []))

    rows = detect_openbb_runtime_capabilities(root=root, endpoints=["equity.profile"])

    assert rows[0]["runtime_available"] is True
    assert rows[0]["provider_key_configured"] is True


def test_endpoint_gap_table_returns_dataframe_when_missing():
    root = types.SimpleNamespace()
    gaps = build_openbb_endpoint_gap_table(root=root)

    assert hasattr(gaps, "columns")
    assert "runtime_available" in gaps.columns or gaps.empty


def test_runtime_matrix_has_fallback_column():
    root = types.SimpleNamespace()
    matrix = build_runtime_capability_matrix(root=root, endpoints=["equity.financials.income"])

    assert "fallback" in matrix.columns
