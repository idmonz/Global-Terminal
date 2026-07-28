from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.no_key_provider_catalog import get_no_key_provider
from lib.provider_probe_runner import run_provider_probe


def _probe(provider_id: str, *, dry_run: bool) -> dict[str, Any]:
    provider = get_no_key_provider(provider_id)
    return run_provider_probe(provider, dry_run=dry_run) if provider else {"provider_id": provider_id, "status": "unavailable", "ok": False}


def build_news_osint_sources_probe(*, dry_run: bool = True) -> dict[str, Any]:
    ids = ["gdelt", "usgs_earthquake", "open_meteo", "nws", "noaa_accessais", "nasa_firms", "aisstream", "opensky"]
    results = [_probe(provider_id, dry_run=dry_run) for provider_id in ids]
    fake_live_guard = {
        "noaa_accessais": "historical-only",
        "aisstream": "live only after key and successful probe",
        "opensky": "live/limited only with credentials or valid anonymous probe",
        "nasa_firms": "missing-key unless MAP_KEY is configured",
    }
    return {"suite": "news_osint_sources", "results": results, "fake_live_guard": fake_live_guard, "dry_run": dry_run}


def _write_output(path: str | None, payload: dict[str, Any]) -> None:
    if path:
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe news and OSINT source readiness.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    payload = build_news_osint_sources_probe(dry_run=args.dry_run)
    _write_output(args.output, payload)
    print(json.dumps({"suite": payload["suite"], "count": len(payload["results"]), "guards": payload["fake_live_guard"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
