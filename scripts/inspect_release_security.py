from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

try:
    from dotenv import dotenv_values
except Exception:  # pragma: no cover
    dotenv_values = None


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {
    ".env",
    ".next",
    "__pycache__",
    "external (2)",
    "node_modules",
    "review_workspace",
}
FORBIDDEN_SUFFIXES = {".db", ".log", ".sqlite", ".sqlite3"}


def inspect_release(zip_path: Path, env_path: Path | None = None) -> dict[str, object]:
    forbidden_entries: list[str] = []
    secret_hits: dict[str, int] = {}
    values: dict[str, bytes] = {}
    if env_path and env_path.exists() and dotenv_values is not None:
        for key, value in dotenv_values(env_path).items():
            encoded = str(value or "").encode("utf-8")
            if len(encoded) >= 8:
                values[str(key)] = encoded

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        for name in names:
            normalized = name.replace("\\", "/")
            parts = set(normalized.split("/"))
            if parts & FORBIDDEN_PARTS or Path(normalized).suffix.lower() in FORBIDDEN_SUFFIXES:
                forbidden_entries.append(normalized)
            if not values:
                continue
            body = archive.read(name)
            for key, encoded in values.items():
                count = body.count(encoded)
                if count:
                    secret_hits[key] = secret_hits.get(key, 0) + count

    return {
        "ok": not forbidden_entries and not secret_hits,
        "zip": zip_path.name,
        "entry_count": len(names),
        "configured_values_checked": len(values),
        "exact_value_hit_count": sum(secret_hits.values()),
        "exact_value_hits_by_name": secret_hits,
        "forbidden_entries": forbidden_entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", nargs="?")
    parser.add_argument("--env", default=str(ROOT / ".env"))
    args = parser.parse_args()
    if args.zip_path:
        zip_path = Path(args.zip_path)
    else:
        candidates = sorted((ROOT / "dist").glob("global_market_terminal_*.zip"))
        if not candidates:
            raise SystemExit("No release archive found.")
        zip_path = candidates[-1]
    report = inspect_release(zip_path.resolve(), Path(args.env).resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
