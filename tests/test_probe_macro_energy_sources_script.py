from __future__ import annotations

from scripts.probe_macro_energy_sources import build_macro_energy_probe, main


def test_probe_macro_energy_sources_missing_keys_nonfatal(tmp_path):
    payload = build_macro_energy_probe(dry_run=True)
    assert payload["suite"] == "macro_energy_sources"
    assert any(item["provider_id"] == "eia" for item in payload["results"])
    output = tmp_path / "macro.json"
    assert main(["--dry-run", "--output", str(output)]) == 0
    assert output.exists()
