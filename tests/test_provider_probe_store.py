from __future__ import annotations

from lib.provider_probe_store import load_provider_probe_results, provider_probe_store_is_gitignored, save_provider_probe_results


def test_provider_probe_store_roundtrip(tmp_path):
    path = tmp_path / "provider_probe_results.json"
    save_provider_probe_results([{"provider_id": "unit", "status": "dry_run"}], path)
    loaded = load_provider_probe_results(path)
    assert loaded["results"][0]["provider_id"] == "unit"
    assert provider_probe_store_is_gitignored()
