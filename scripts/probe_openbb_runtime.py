from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from importlib import metadata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_openbb_runtime_probe(*, sample: bool = False, dry_run: bool = True) -> dict[str, Any]:
    installed = importlib.util.find_spec("openbb") is not None
    version = None
    if installed:
        try:
            version = metadata.version("openbb")
        except Exception:
            version = "installed-version-unknown"
    resolver_ok = False
    resolver_error = None
    try:
        import lib.openbb_endpoint_resolver as resolver

        resolver_ok = True
        resolver_exports = [name for name in ("resolve_endpoint_path", "resolve_openbb_endpoint_path") if hasattr(resolver, name)]
    except Exception as exc:
        resolver_exports = []
        resolver_error = str(exc)
    sample_status = "skipped"
    if sample:
        sample_status = "dry_run" if dry_run else "not_run_network_disabled"
    return {
        "suite": "openbb_runtime",
        "ok": True,
        "installed": installed,
        "version": version,
        "endpoint_resolver_ok": resolver_ok,
        "endpoint_resolver_exports": resolver_exports,
        "endpoint_resolver_error": resolver_error,
        "sample_status": sample_status,
        "status": "available" if installed else "optional_missing",
        "caveat": "OpenBB is optional; base launch does not require it.",
    }


def _write_output(path: str | None, payload: dict[str, Any]) -> None:
    if path:
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe optional OpenBB runtime.")
    parser.add_argument("--sample", action="store_true", help="Include a nonfatal sample-query status.")
    parser.add_argument("--dry-run", action="store_true", help="Do not run runtime sample calls.")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args(argv)
    payload = build_openbb_runtime_probe(sample=args.sample, dry_run=args.dry_run)
    _write_output(args.output, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
