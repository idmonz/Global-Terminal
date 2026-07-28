from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
MAX_PATTERN_SCAN_BYTES = 5 * 1024 * 1024

FORBIDDEN_ROOTS = {
    ".env",
    "dist",
    "external",
    "external (2)",
    "review_workspace",
    "_recovery",
}
FORBIDDEN_PARTS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".temp",
    "__pycache__",
    "node_modules",
}
FORBIDDEN_SUFFIXES = {
    ".7z",
    ".db",
    ".key",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
    ".rar",
    ".sqlite",
    ".sqlite3",
    ".zip",
}
TOKEN_PATTERNS = (
    re.compile(rb"(?<![A-Za-z0-9_])AIza[0-9A-Za-z_-]{24,}"),
    re.compile(rb"(?<![A-Za-z0-9_])sk-(?:proj-|live-)?[0-9A-Za-z_-]{20,}"),
    re.compile(rb"(?<![A-Za-z0-9_])sb_secret_[0-9A-Za-z_-]{16,}"),
    re.compile(rb"(?<![A-Za-z0-9_])gh[pousr]_[0-9A-Za-z]{20,}"),
    re.compile(rb"(?<![A-Za-z0-9_])eyJ[0-9A-Za-z_-]{20,}\.[0-9A-Za-z_-]{10,}\.[0-9A-Za-z_-]{10,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
PLACEHOLDER_MARKERS = (
    b"dummy",
    b"example",
    b"fake",
    b"fixture",
    b"local",
    b"phase6q",
    b"should_never_be_printed",
    b"test",
)


def collect_git_candidates(root: Path = ROOT) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    paths = [Path(item.decode("utf-8")) for item in completed.stdout.split(b"\0") if item]
    return sorted(path for path in paths if (root / path).is_file())


def _dotenv_values(path: Path) -> list[bytes]:
    if not path.exists():
        return []
    values: list[bytes] = []
    for raw_line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        value = line.split("=", 1)[1].strip().strip('"').strip("'")
        encoded = value.encode("utf-8")
        if len(encoded) >= 8:
            values.append(encoded)
    return values


def _forbidden_path(path: Path) -> bool:
    posix = path.as_posix()
    if not path.parts:
        return True
    if path.parts[0].lower() in {item.lower() for item in FORBIDDEN_ROOTS}:
        return True
    if any(part.lower() in FORBIDDEN_PARTS for part in path.parts):
        return True
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return True
    return posix.startswith("data/private/") or posix.startswith("data/cache/")


def _is_reviewed_test_placeholder(path: Path, match: bytes) -> bool:
    if not path.as_posix().startswith("tests/"):
        return False
    lowered = match.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def audit_git_candidates(
    root: Path,
    paths: Iterable[Path],
    *,
    env_path: Path | None = None,
    max_pattern_scan_bytes: int = MAX_PATTERN_SCAN_BYTES,
) -> dict[str, object]:
    candidates = list(paths)
    configured_values = _dotenv_values(env_path) if env_path else []
    forbidden_paths: list[str] = []
    exact_value_hit_paths: set[str] = set()
    token_pattern_hit_paths: set[str] = set()
    reviewed_placeholder_count = 0
    large_pattern_scan_skips = 0
    total_bytes = 0

    for relative in candidates:
        absolute = root / relative
        if not absolute.is_file():
            continue
        normalized = relative.as_posix()
        total_bytes += absolute.stat().st_size
        if _forbidden_path(relative):
            forbidden_paths.append(normalized)
        body = absolute.read_bytes()
        if any(value in body for value in configured_values):
            exact_value_hit_paths.add(normalized)
        if len(body) > max_pattern_scan_bytes:
            large_pattern_scan_skips += 1
            continue
        for pattern in TOKEN_PATTERNS:
            for matched in pattern.finditer(body):
                value = matched.group(0)
                if _is_reviewed_test_placeholder(relative, value):
                    reviewed_placeholder_count += 1
                else:
                    token_pattern_hit_paths.add(normalized)

    passed = not forbidden_paths and not exact_value_hit_paths and not token_pattern_hit_paths
    return {
        "evidence_version": "phase6q.git-publish-audit.v1",
        "passed": passed,
        "redacted": True,
        "candidate_file_count": len(candidates),
        "candidate_total_bytes": total_bytes,
        "configured_value_count": len(configured_values),
        "exact_value_hit_count": len(exact_value_hit_paths),
        "exact_value_hit_paths": sorted(exact_value_hit_paths),
        "forbidden_path_count": len(forbidden_paths),
        "forbidden_paths": sorted(forbidden_paths),
        "token_pattern_hit_count": len(token_pattern_hit_paths),
        "token_pattern_hit_paths": sorted(token_pattern_hit_paths),
        "reviewed_test_placeholder_count": reviewed_placeholder_count,
        "large_pattern_scan_skip_count": large_pattern_scan_skips,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Git publish candidates without printing secret values.")
    parser.add_argument("--env", default=str(ROOT / ".env"))
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit_git_candidates(ROOT, collect_git_candidates(ROOT), env_path=Path(args.env))
    encoded = json.dumps(result, indent=2, sort_keys=True)
    print(encoded)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
