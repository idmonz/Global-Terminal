from __future__ import annotations

from scripts.probe_crypto_sources import build_crypto_sources_probe, main


def test_probe_crypto_sources_dry_run_has_public_sources(tmp_path):
    payload = build_crypto_sources_probe(dry_run=True)
    ids = {item["provider_id"] for item in payload["results"]}
    assert {"binance_public", "defillama", "coingecko_public"} <= ids
    output = tmp_path / "crypto.json"
    assert main(["--dry-run", "--output", str(output)]) == 0
    assert output.exists()
