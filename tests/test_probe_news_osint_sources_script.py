from __future__ import annotations

from scripts.probe_news_osint_sources import build_news_osint_sources_probe, main


def test_probe_news_osint_sources_guards_fake_live_claims(tmp_path):
    payload = build_news_osint_sources_probe(dry_run=True)
    assert payload["fake_live_guard"]["noaa_accessais"] == "historical-only"
    assert "successful probe" in payload["fake_live_guard"]["aisstream"]
    output = tmp_path / "news.json"
    assert main(["--dry-run", "--output", str(output)]) == 0
    assert output.exists()
