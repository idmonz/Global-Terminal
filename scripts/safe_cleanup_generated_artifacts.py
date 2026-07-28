from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "docs" / "RECOVERY_CLEANUP_LOG.md"
ALLOWED_FILE_SUFFIXES = {".pyc", ".pyo", ".log"}
ALLOWED_DIR_NAMES = {"__pycache__", ".pytest_cache"}
ALLOWED_EXACT_DIRS = {ROOT / "data" / "cache"}
SOURCE_SUFFIXES = {".py", ".md", ".csv", ".json", ".toml", ".ini", ".txt", ".yaml", ".yml"}


def _is_inside_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def _is_allowed_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in ALLOWED_FILE_SUFFIXES


def _is_allowed_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    if path.name in ALLOWED_DIR_NAMES:
        return True
    return path.resolve() in {item.resolve() for item in ALLOWED_EXACT_DIRS}


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _is_inside_allowed_dir(path: Path, dirs: list[Path]) -> bool:
    return any(_is_inside(path, directory) for directory in dirs)


def _refuse_source_file(path: Path) -> None:
    if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES and path.suffix.lower() not in ALLOWED_FILE_SUFFIXES:
        raise RuntimeError(f"Refusing to remove source-like file: {path}")


def discover_artifacts() -> list[Path]:
    allowed_dirs: list[Path] = []
    allowed_files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not _is_inside_root(path):
            raise RuntimeError(f"Refusing path outside project root: {path}")
        if _is_allowed_dir(path):
            allowed_dirs.append(path)
    for path in ROOT.rglob("*"):
        if not _is_inside_root(path):
            raise RuntimeError(f"Refusing path outside project root: {path}")
        if _is_inside_allowed_dir(path, allowed_dirs):
            continue
        if _is_allowed_file(path):
            _refuse_source_file(path)
            allowed_files.append(path)
    return sorted(allowed_files, key=lambda item: str(item), reverse=True) + sorted(allowed_dirs, key=lambda item: (len(item.parts), str(item)), reverse=True)


def remove_artifact(path: Path) -> None:
    if not _is_inside_root(path):
        raise RuntimeError(f"Refusing path outside project root: {path}")
    if not (_is_allowed_dir(path) or _is_allowed_file(path)):
        raise RuntimeError(f"Refusing unsupported cleanup target: {path}")
    _refuse_source_file(path)
    if path.is_dir():
        for child in sorted(path.rglob("*"), key=lambda item: (len(item.parts), str(item)), reverse=True):
            if not _is_inside_root(child):
                raise RuntimeError(f"Refusing path outside project root: {child}")
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()
    elif path.is_file():
        path.unlink()


def write_log(paths: list[Path], *, executed: bool, skipped: list[tuple[Path, str]] | None = None) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    mode = "execute" if executed else "dry-run"
    lines = [
        "# Recovery Cleanup Log",
        "",
        f"- timestamp_utc: {datetime.now(timezone.utc).isoformat()}",
        f"- mode: {mode}",
        "- project_root_label: release_root",
        f"- artifacts_detected: {len(paths)}",
        "",
        "## Targets",
        "",
    ]
    if paths:
        lines.extend(f"- `{path.relative_to(ROOT)}`" for path in paths)
    else:
        lines.append("- No generated artifacts found.")
    if skipped:
        lines.extend(["", "## Skipped", ""])
        lines.extend(f"- `{path.relative_to(ROOT)}`: {reason}" for path, reason in skipped)
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely clean generated artifacts from this project.")
    parser.add_argument("--dry-run", action="store_true", help="List cleanup targets without deleting them. This is the default.")
    parser.add_argument("--execute", action="store_true", help="Actually remove approved generated artifacts.")
    args = parser.parse_args()

    if args.execute and args.dry_run:
        parser.error("Choose either --dry-run or --execute, not both.")

    paths = discover_artifacts()
    executed = bool(args.execute)
    skipped: list[tuple[Path, str]] = []
    if executed:
        for path in paths:
            if path.exists():
                try:
                    remove_artifact(path)
                except PermissionError as exc:
                    skipped.append((path, str(exc)))
    write_log(paths, executed=executed, skipped=skipped)
    action = "removed" if executed else "would remove"
    print(f"{action} {len(paths)} generated artifact(s)")
    for path in paths:
        print(path.relative_to(ROOT))
    if skipped:
        print(f"skipped {len(skipped)} locked artifact(s)")
        for path, reason in skipped:
            print(f"locked: {path.relative_to(ROOT)} ({reason})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
