from __future__ import annotations

from scripts.probe_openbb_runtime import build_openbb_runtime_probe, main


def test_probe_openbb_runtime_is_nonfatal(tmp_path):
    payload = build_openbb_runtime_probe(sample=True, dry_run=True)
    assert payload["ok"] is True
    output = tmp_path / "openbb.json"
    assert main(["--dry-run", "--output", str(output)]) == 0
    assert output.exists()
