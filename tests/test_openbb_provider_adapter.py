from __future__ import annotations

import types

import pandas as pd

from lib import openbb_bridge
from lib.openbb_provider_adapter import get_openbb_company_profile, get_openbb_price_history


def test_adapter_missing_openbb_returns_warning(monkeypatch):
    monkeypatch.delitem(openbb_bridge.sys.modules, "openbb", raising=False)
    monkeypatch.setattr(openbb_bridge.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(openbb_bridge.importlib, "import_module", lambda name: (_ for _ in ()).throw(ImportError("missing")))

    result = get_openbb_company_profile("AAPL")

    assert not result.ok
    assert result.is_openbb is True
    assert result.is_optional is True


def test_adapter_mock_price_history_maps_schema(monkeypatch):
    fake_obb = types.SimpleNamespace(
        equity=types.SimpleNamespace(
            price=types.SimpleNamespace(
                historical=lambda **kwargs: [{"date": "2024-01-01", "close": 100.0}]
            )
        )
    )
    monkeypatch.setitem(openbb_bridge.sys.modules, "openbb", types.SimpleNamespace(obb=fake_obb))

    result = get_openbb_price_history("AAPL")

    assert result.ok
    assert isinstance(result.data, pd.DataFrame)
    assert "close" in result.data.columns
    assert result.provider == "openbb"
