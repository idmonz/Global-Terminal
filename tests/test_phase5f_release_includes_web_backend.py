from __future__ import annotations

import zipfile

from scripts import build_release_zip


REQUIRED_PRODUCT_FILES = {
    ".github/action-pins.json",
    ".github/dependabot.yml",
    ".github/workflows/phase6q-hosted-observation.yml",
    ".github/workflows/quality-gate.yml",
    "requirements-api.txt",
    "apps/web/package.json",
    "apps/web/package-lock.json",
    "apps/web/src/app/page.tsx",
    "apps/web/src/app/globals.css",
    "apps/web/src/lib/contracts.ts",
    "backend/api/app.py",
    "docs/PHASE_6Q_HOSTED_DEPLOYMENT_HANDOFF.md",
    "docs/PHASE_6Q_HOSTED_RLS_EVIDENCE_REPORT.md",
    "lib/hosted_scheduler_operations.py",
    "lib/hosted_scheduler_worker.py",
    "scripts/verify_phase6q_hosted_evidence.py",
    "scripts/verify_phase6q_hosted_rls_summary.py",
    "scripts/audit_git_publish.py",
    "scripts/validate_github_workflows.py",
    "scripts/verify_phase6q_remote_anonymous_denial.py",
    "scripts/test-phase6q-hosted-scheduler-rls.ps1",
    "supabase/migrations/20260727143000_phase6q_hosted_observation_scheduler.sql",
    "supabase/migrations/20260727190000_phase6q_deleted_schedule_recreation.sql",
    "supabase/migrations/20260727191500_phase6q_remove_legacy_owner_constraint.sql",
}


def test_phase5f_release_file_selection_includes_first_party_web_and_backend():
    names = {path.relative_to(build_release_zip.ROOT).as_posix() for path in build_release_zip.iter_release_files()}

    assert REQUIRED_PRODUCT_FILES <= names
    assert not any("node_modules" in name for name in names)
    assert not any("/.next/" in f"/{name}/" for name in names)
    assert not any(name.startswith("external") for name in names)
    assert "docs/PHASE_5F_EXTERNAL_FULL_INVENTORY.csv" not in names
    assert not any(name.startswith("data/private/") for name in names)
    assert ".env" not in names


def test_phase5f_built_release_contains_product_source_and_excludes_generated_trees(tmp_path, monkeypatch):
    monkeypatch.setattr(build_release_zip, "DIST", tmp_path / "dist")
    monkeypatch.setattr(build_release_zip, "REPORT", tmp_path / "RELEASE_PACKAGE_REPORT.md")

    zip_path, manifest = build_release_zip.build_release()

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())

    assert REQUIRED_PRODUCT_FILES <= names
    assert REQUIRED_PRODUCT_FILES <= set(manifest["files"])
    assert not any("node_modules" in name or "/.next/" in f"/{name}/" for name in names)
    assert not any(name.startswith("external") or name.startswith("data/private/") for name in names)
    assert not any(name == ".env" or name.endswith("/secrets.toml") for name in names)
