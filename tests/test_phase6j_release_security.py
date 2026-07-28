from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.inspect_release_security import inspect_release
from scripts.build_release_zip import ROOT, iter_release_files


def _archive(path: Path, entries: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, body in entries.items():
            archive.writestr(name, body)
    return path


def test_phase6j_release_inspector_rejects_exact_secret_and_private_paths(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("TEST_RELEASE_SECRET=phase6j-secret-value\n", encoding="utf-8")
    unsafe = _archive(
        tmp_path / "unsafe.zip",
        {
            "lib/safe.py": b"phase6j-secret-value",
            "review_workspace/account.db": b"private",
        },
    )
    report = inspect_release(unsafe, env)
    assert report["ok"] is False
    assert report["exact_value_hits_by_name"] == {"TEST_RELEASE_SECRET": 1}
    assert report["forbidden_entries"] == ["review_workspace/account.db"]


def test_phase6j_release_inspector_accepts_secret_free_archive(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("TEST_RELEASE_SECRET=phase6j-secret-value\n", encoding="utf-8")
    safe = _archive(tmp_path / "safe.zip", {"lib/safe.py": b"print('safe')"})
    report = inspect_release(safe, env)
    assert report["ok"] is True
    assert report["exact_value_hit_count"] == 0


def test_phase6j_release_includes_optional_rls_migration_without_private_data():
    names = {path.relative_to(ROOT).as_posix() for path in iter_release_files()}
    assert "supabase/migrations/20260710105056_phase6j_tenant_preferences.sql" in names
    assert not any(name.endswith((".db", ".sqlite", ".sqlite3")) for name in names)
