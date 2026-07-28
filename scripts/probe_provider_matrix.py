from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.provider_probe_runner import build_provider_probe_summary, run_all_lightweight_probes
from lib.provider_probe_store import save_provider_probe_results


def build_provider_matrix_probe(*, dry_run: bool = True, save_default: bool = False) -> dict[str, Any]:
    results = run_all_lightweight_probes(dry_run=dry_run, save=False)
    if save_default and not dry_run:
        save_provider_probe_results(results)
    coverage = Counter(str(item.get("source_type") or "unknown") for item in results)
    missing_keys = [item for item in results if item.get("status") == "missing_key"]
    return {
        "suite": "provider_matrix",
        "summary": build_provider_probe_summary(results),
        "domain_coverage": dict(coverage),
        "missing_keys": missing_keys,
        "results": results,
        "dry_run": dry_run,
    }


def _write_output(path: str | None, payload: dict[str, Any]) -> None:
    if path:
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe lightweight provider matrix.")
    parser.add_argument("--dry-run", action="store_true", help="Return statuses without network requests or writes.")
    parser.add_argument("--save-default", action="store_true", help="Write provider_probe_results.json through the gitignored store when not dry-run.")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args(argv)
    payload = build_provider_matrix_probe(dry_run=args.dry_run, save_default=args.save_default)
    _write_output(args.output, payload)
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
