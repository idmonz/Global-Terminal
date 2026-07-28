from __future__ import annotations

from lib import openbb_real_probe


def test_real_probe_skips_when_openbb_missing(monkeypatch):
    monkeypatch.setattr(openbb_real_probe, "is_openbb_installed", lambda: False)

    report = openbb_real_probe.run_openbb_installation_probe()
    sample = openbb_real_probe.run_openbb_sample_query_probe("sample", lambda: None)

    assert report["skipped"] is True
    assert sample["skipped"] is True


def test_endpoint_probe_supports_mock_root():
    import types

    root = types.SimpleNamespace(equity=types.SimpleNamespace(profile=lambda **kwargs: []))
    report = openbb_real_probe.run_openbb_endpoint_probe("equity.profile", root=root)

    assert report["ok"] is True
