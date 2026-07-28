from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.env_loader import get_env_var, load_project_env
from lib.provider_probe_runner import run_provider_probe
from lib.no_key_provider_catalog import get_no_key_provider


def _probe_catalog(provider_id: str, *, dry_run: bool) -> dict[str, Any]:
    provider = get_no_key_provider(provider_id)
    if provider is None:
        return {"provider_id": provider_id, "ok": False, "status": "unavailable", "warning": "Provider is not in catalog.", "dry_run": dry_run}
    return run_provider_probe(provider, dry_run=dry_run)


def build_macro_energy_probe(*, dry_run: bool = True) -> dict[str, Any]:
    load_project_env()
    results = [
        _probe_catalog("treasury_fiscal", dry_run=dry_run),
        _probe_catalog("worldbank", dry_run=dry_run),
        _probe_catalog("sdmx", dry_run=dry_run),
        _probe_catalog("fred", dry_run=dry_run),
        _probe_catalog("eia", dry_run=dry_run),
        {"provider_id": "bls", "provider": "BLS", "ok": True, "status": "configured" if get_env_var("BLS_API_KEY") else "no_key_fallback", "configured": bool(get_env_var("BLS_API_KEY")), "dry_run": dry_run, "source_type": "official", "warning": "BLS key is optional for base launch; endpoint coverage varies."},
        _probe_catalog("open_meteo", dry_run=dry_run),
    ]
    return {"suite": "macro_energy_sources", "results": results, "missing_keys": [item for item in results if item.get("status") == "missing_key"], "dry_run": dry_run}


def _write_output(path: str | None, payload: dict[str, Any]) -> None:
    if path:
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe macro and energy source readiness.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    payload = build_macro_energy_probe(dry_run=args.dry_run)
    _write_output(args.output, payload)
    print(json.dumps({"suite": payload["suite"], "count": len(payload["results"]), "missing_keys": len(payload["missing_keys"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
