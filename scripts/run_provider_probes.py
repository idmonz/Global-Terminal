from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.provider_probe_runner import build_probe_summary, run_provider_probes
from lib.provider_probe_store import save_provider_probe_results
from scripts.probe_crypto_sources import build_crypto_sources_probe
from scripts.probe_macro_energy_sources import build_macro_energy_probe
from scripts.probe_news_osint_sources import build_news_osint_sources_probe
from scripts.probe_openbb_runtime import build_openbb_runtime_probe
from scripts.probe_provider_matrix import build_provider_matrix_probe


def _write_output(path: str | None, payload) -> None:
    if path:
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run lightweight Goal 10 provider probes.")
    parser.add_argument("--dry-run", action="store_true", help="Build probe statuses without network requests or writes.")
    parser.add_argument("--save", action="store_true", help="Save results to gitignored private storage.")
    parser.add_argument("--suite", choices=["all", "matrix", "openbb", "macro-energy", "crypto", "news-osint"], default="all", help="Optional split probe suite to run.")
    parser.add_argument("--output", help="Optional JSON output path.")
    parser.add_argument("providers", nargs="*", help="Optional provider ids to probe.")
    args = parser.parse_args()

    if args.suite != "all":
        builders = {
            "matrix": lambda: build_provider_matrix_probe(dry_run=args.dry_run, save_default=args.save),
            "openbb": lambda: build_openbb_runtime_probe(sample=False, dry_run=args.dry_run),
            "macro-energy": lambda: build_macro_energy_probe(dry_run=args.dry_run),
            "crypto": lambda: build_crypto_sources_probe(dry_run=args.dry_run),
            "news-osint": lambda: build_news_osint_sources_probe(dry_run=args.dry_run),
        }
        payload = builders[args.suite]()
        _write_output(args.output, payload)
        print(json.dumps({"suite": args.suite, "status": "ok"}, indent=2))
        return 0

    results = run_provider_probes(args.providers or None, dry_run=args.dry_run, save=False)
    if args.save and not args.dry_run:
        save_provider_probe_results(results)
    summary = build_probe_summary(results)
    _write_output(args.output, {"suite": "all", "summary": summary, "results": results, "dry_run": args.dry_run})
    print(f"provider probes: total={summary['total']} ready={summary['ready']} gaps={summary['gaps']} status={summary['status']}")
    for result in results:
        print(f"{result['provider_id']}: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
