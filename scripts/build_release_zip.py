from __future__ import annotations

import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST = ROOT / "dist"
DIST = DEFAULT_DIST
REPORT = ROOT / "docs" / "RELEASE_PACKAGE_REPORT.md"
MANIFEST_NAME = "release_manifest.json"

INCLUDE_ROOTS = [
    "AGENTS.md",
    ".agents",
    ".github",
    ".gitignore",
    ".env.example",
    "app.py",
    "requirements.txt",
    "requirements-api.txt",
    "requirements-openbb.txt",
    "pytest.ini",
    "README.md",
    "lib",
    "pages",
    "tests",
    "static",
    "docs",
    "scripts",
    "apps",
    "backend",
    "supabase",
]

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".next",
    ".turbo",
    "external",
    "_recovery",
    "data",
    "dist",
    "node_modules",
    "build",
    "coverage",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".duckdb",
    ".ckpt",
    ".h5",
    ".joblib",
    ".onnx",
    ".pt",
    ".pth",
    ".safetensors",
}
EXCLUDED_NAMES = {".env", "secrets.toml", "provider_probe_results.json"}
EXCLUDED_NAME_TOKENS = {
    "OpenBB-develop",
    "worldmonitor-main",
    "OpenStock",
    "OpenAlice",
    "FinceptTerminal",
    "finvizfinance",
    "bloomberg-terminal",
    "Bloomberg-terminal",
    "BB-Terminal",
    "quant-traderr-lab",
    "optlib",
    "osiris",
    "agent-skills",
    "agent-skills-main",
    "Kronos",
    "Kronos-master",
    "QuantDinger",
    "QuantDinger-main",
    "tensortrade",
    "tensortrade-master",
    "worldview",
    "worldview-main",
    "checkpoint",
    "local_option_chain",
    "model_weights",
    "option_chain_upload",
    "options_chain_upload",
    "uploaded_option_chain",
    "actionless_simulations",
}
EXCLUDED_PREFIXES = {"data/cache/", "data/private/", "data/private/actionless_simulations/", "data/provider_probe_results.json"}


def _is_excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    rel_posix = rel.as_posix()
    parts = set(rel.parts)
    if parts & EXCLUDED_PARTS:
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if path.name in EXCLUDED_NAMES:
        return True
    if path.name.startswith("CODEX_"):
        return True
    if path.name.startswith(".env.") and path.name != ".env.example":
        return True
    if any(token in path.name for token in EXCLUDED_NAME_TOKENS):
        return True
    if path.suffix.lower() == ".csv" and not (
        rel_posix.startswith("static/index_constituents/")
        or rel_posix.startswith("tests/fixtures/")
    ):
        return True
    if ".streamlit" in parts:
        return True
    if any(rel_posix.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return True
    return False


def iter_release_files() -> list[Path]:
    files: list[Path] = []
    for item in INCLUDE_ROOTS:
        path = ROOT / item
        if not path.exists() or _is_excluded(path):
            continue
        if path.is_file():
            files.append(path)
            continue
        for child in path.rglob("*"):
            if child.is_file() and not _is_excluded(child):
                files.append(child)
    return sorted(set(files), key=lambda value: value.relative_to(ROOT).as_posix())


def build_release() -> tuple[Path, dict]:
    DIST.mkdir(exist_ok=True)
    env_timestamp = os.environ.get("RELEASE_ZIP_TIMESTAMP", "").strip()
    timestamp = env_timestamp if re.match(r"^\d{8}T\d{6}Z$", env_timestamp) else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    zip_path = DIST / f"global_market_terminal_{timestamp}.zip"
    zip_name = zip_path.name
    files = iter_release_files()
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root_label": "release_root",
        "zip_name": zip_name,
        "zip_path": f"dist/{zip_name}",
        "selected_file_count": len(files),
        "manifest_entry_count": 1,
        "expected_zip_entry_count": len(files) + 1,
        "actual_zip_entry_count": len(files) + 1,
        "file_count": len(files),
        "excluded": sorted(EXCLUDED_PARTS | EXCLUDED_PREFIXES | EXCLUDED_NAME_TOKENS | {f"*{suffix}" for suffix in EXCLUDED_SUFFIXES} | EXCLUDED_NAMES),
        "files": [path.relative_to(ROOT).as_posix() for path in files],
    }
    # Write the package report before archiving so the zip contains the same
    # unambiguous count terminology that the post-build report uses.
    write_report(zip_path, manifest)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    with zipfile.ZipFile(zip_path) as archive:
        manifest["actual_zip_entry_count"] = len(archive.namelist())
    if DIST.resolve() == DEFAULT_DIST.resolve():
        (ROOT / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return zip_path, manifest


def write_report(zip_path: Path, manifest: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Release Package Report",
        "",
        f"- created_at_utc: {manifest['created_at_utc']}",
        f"- zip_path: `{manifest.get('zip_path', zip_path.name)}`",
        f"- selected_file_count_before_manifest: {manifest['selected_file_count']}",
        f"- manifest_entry_count: {manifest['manifest_entry_count']}",
        f"- expected_zip_entry_count_after_manifest: {manifest['expected_zip_entry_count']}",
        f"- actual_zip_entry_count_after_manifest: {manifest.get('actual_zip_entry_count', manifest['expected_zip_entry_count'])}",
        f"- legacy_file_count_alias: {manifest['file_count']}",
        "- external_excluded: true",
        "- data_cache_excluded: true",
        "- secrets_excluded: true",
        "- generated_artifacts_excluded: true",
        "",
        "## Exclusions",
        "",
    ]
    lines.extend(f"- `{item}`" for item in manifest["excluded"])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    zip_path, manifest = build_release()
    write_report(zip_path, manifest)
    print(f"release zip: {zip_path}")
    print(f"files selected before manifest: {manifest['selected_file_count']}")
    print(f"zip entries after manifest: {manifest.get('actual_zip_entry_count', manifest['expected_zip_entry_count'])}")
    print(f"files packaged: {manifest['file_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
