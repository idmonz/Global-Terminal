from __future__ import annotations

import types

from lib.openbb_endpoint_resolver import endpoint_path_exists, get_nested_attr_safe, resolve_openbb_endpoint_path, select_first_available_endpoint


def test_resolver_handles_mock_nested_object():
    root = types.SimpleNamespace(equity=types.SimpleNamespace(fundamental=types.SimpleNamespace(income=lambda **kwargs: [])))

    report = resolve_openbb_endpoint_path("equity.financials.income", root=root)

    assert report["available"] is True
    assert report["selected_path"] == "equity.fundamental.income"
    assert endpoint_path_exists(root, "equity.fundamental.income")


def test_get_nested_attr_safe_returns_reason():
    root = types.SimpleNamespace()
    target, error = get_nested_attr_safe(root, "missing.path")

    assert target is None
    assert "Missing path component" in error


def test_select_first_available_endpoint_reports_unavailable():
    root = types.SimpleNamespace()

    report = select_first_available_endpoint(["a.b", "c.d"], root=root)

    assert report["available"] is False
