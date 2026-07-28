from __future__ import annotations

from scripts.probe_provider_matrix import build_provider_matrix_probe, main


def test_probe_provider_matrix_dry_run_outputs_summary(tmp_path):
    payload = build_provider_matrix_probe(dry_run=True)
    assert payload["summary"]["total"] >= 1
    output = tmp_path / "matrix.json"
    assert main(["--dry-run", "--output", str(output)]) == 0
    assert output.exists()
