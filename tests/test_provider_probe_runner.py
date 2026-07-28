from __future__ import annotations

from lib.provider_probe_runner import build_probe_summary, probe_provider, run_provider_probes


def test_provider_probe_missing_key_nonfatal(monkeypatch):
    monkeypatch.delenv("UNIT_REQUIRED_KEY", raising=False)
    results = [
        probe_provider(
            {
                "provider_id": "unit_required",
                "name": "Unit Required",
                "env_var": "UNIT_REQUIRED_KEY",
                "key_required": True,
                "no_key_fallback": False,
                "source_type": "unit",
                "caveat": "Unit test provider.",
            },
            dry_run=True,
        )
    ]
    assert results[0]["status"] == "missing_key"
    assert build_probe_summary(results)["gaps"] == 1
