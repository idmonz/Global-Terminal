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
from lib.no_key_provider_catalog import get_no_key_provider
from lib.provider_probe_runner import run_provider_probe


def _probe(provider_id: str, *, dry_run: bool) -> dict[str, Any]:
    provider = get_no_key_provider(provider_id)
    return run_provider_probe(provider, dry_run=dry_run) if provider else {"provider_id": provider_id, "status": "unavailable", "ok": False}


def build_crypto_sources_probe(*, dry_run: bool = True) -> dict[str, Any]:
    load_project_env()
    results = [_probe("binance_public", dry_run=dry_run), _probe("defillama", dry_run=dry_run), _probe("coingecko_public", dry_run=dry_run)]
    results.append({"provider_id": "coingecko_demo", "provider": "CoinGecko Demo", "ok": True, "status": "configured" if get_env_var("COINGECKO_API_KEY") else "no_key_fallback", "configured": bool(get_env_var("COINGECKO_API_KEY")), "dry_run": dry_run, "warning": "Keyless CoinGecko fallback is rate-limited."})
    return {"suite": "crypto_sources", "results": results, "dry_run": dry_run, "rate_limit_policy": "dry-run by default; live calls must respect provider limits."}


def _write_output(path: str | None, payload: dict[str, Any]) -> None:
    if path:
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe crypto source readiness.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    payload = build_crypto_sources_probe(dry_run=args.dry_run)
    _write_output(args.output, payload)
    print(json.dumps({"suite": payload["suite"], "count": len(payload["results"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
