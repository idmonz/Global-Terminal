from __future__ import annotations

import types

import pandas as pd

from lib import openbb_bridge


def test_openbb_missing_returns_graceful_warning(monkeypatch):
    monkeypatch.delitem(openbb_bridge.sys.modules, "openbb", raising=False)
    monkeypatch.setattr(openbb_bridge.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(openbb_bridge.importlib, "import_module", lambda name: (_ for _ in ()).throw(ImportError("missing")))

    result = openbb_bridge.call_openbb_command_safe("equity.profile", symbol="AAPL")

    assert not result.ok
    assert result.provider == "openbb"
    assert result.is_optional is True
    assert "not installed" in result.error.lower()


def test_openbb_mock_command_normalizes_dataframe(monkeypatch):
    fake_obb = types.SimpleNamespace(
        equity=types.SimpleNamespace(
            profile=lambda **kwargs: [{"symbol": kwargs["symbol"], "name": "Example Inc"}],
        )
    )
    module = types.SimpleNamespace(obb=fake_obb, __version__="mock")
    monkeypatch.setitem(openbb_bridge.sys.modules, "openbb", module)

    result = openbb_bridge.call_openbb_command_safe("equity.profile", symbol="AAPL")

    assert result.ok
    assert isinstance(result.data, pd.DataFrame)
    assert result.data.iloc[0]["symbol"] == "AAPL"
    assert result.command == "equity.profile"
