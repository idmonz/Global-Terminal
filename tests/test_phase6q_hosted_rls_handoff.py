from __future__ import annotations

import re
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.preflight_phase6q_hosted_deployment import _migration_is_remote, build_preflight
from scripts.verify_phase6q_hosted_rls_summary import validate_phase6q_hosted_rls_summary


ROOT = Path(__file__).resolve().parents[1]


def test_phase6q_preflight_requires_both_remote_migrations():
    aligned = """
       Local          | Remote         | Time (UTC)
      ----------------|----------------|----------------
       `20260727143000` | `20260727143000` | `20260727143000`
       `20260727190000` | `20260727190000` | `20260727190000`
       `20260727191500` | `20260727191500` | `20260727191500`
    """
    base_only = "`20260727143000` | `20260727143000` | `20260727143000`"
    json_output = json.dumps(
        {
            "migrations": [
                {"local": "20260727143000", "remote": "20260727143000"},
                {"local": "20260727190000", "remote": "20260727190000"},
                {"local": "20260727191500", "remote": "20260727191500"},
            ]
        }
    )

    assert _migration_is_remote(aligned) is True
    assert _migration_is_remote(json_output) is True
    assert _migration_is_remote(base_only) is False


def test_phase6q_deleted_schedule_hardening_preserves_one_active_and_allows_recreation():
    sql = (
        ROOT / "supabase/migrations/20260727190000_phase6q_deleted_schedule_recreation.sql"
    ).read_text(encoding="utf-8")

    assert "drop constraint if exists global_terminal_hosted_observation_schedules_tenant_id_owner_user_key" in sql
    assert "global_terminal_hosted_schedule_one_active_owner_idx" in sql
    assert "where state <> 'deleted'" in sql
    assert "drop table" not in sql.lower()
    assert re.search(r"\btruncate\s+table\b", sql, re.IGNORECASE) is None

    repair = (
        ROOT / "supabase/migrations/20260727191500_phase6q_remove_legacy_owner_constraint.sql"
    ).read_text(encoding="utf-8")
    assert "pg_catalog.pg_constraint" in repair
    assert "constraint_row.contype = 'u'" in repair
    assert "array['tenant_id', 'owner_user_id']::name[]" in repair
    assert "execute format" in repair
    assert "where state <> 'deleted'" in repair
    assert "drop table" not in repair.lower()
    assert re.search(r"\btruncate\s+table\b", repair, re.IGNORECASE) is None


def test_phase6q_hosted_rls_handoff_is_secret_safe_bounded_and_cleanup_first():
    script = (ROOT / "scripts/test-phase6q-hosted-scheduler-rls.ps1").read_text(encoding="utf-8")

    for marker in (
        "Read-Host \"$Label password\" -AsSecureString",
        "global_terminal_apply_hosted_observation_schedule",
        "global_terminal_apply_account_document",
        "Account B cannot read Account A hosted scheduler evidence",
        "Stale hosted schedule update returns an optimistic conflict",
        "A deleted schedule no longer blocks one replacement schedule",
        "Account A restores the exact original research-continuity payload",
        "Hosted cleanup re-reads the original account document without temporary parents",
        "operator_gate_changed = $false",
        "hosted_worker_invoked = $false",
        "hosted_scheduler_verified = $false",
        "provider_call_count = 0",
        "Close-TestSchedule",
        '$script:RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot ".."))',
        'Join-Path $script:RepoRoot ".env"',
        'Join-Path $script:RepoRoot "review_workspace\\phase6q_hosted_rls_summary.json"',
        'Join-Path $script:RepoRoot "scripts\\verify_phase6q_hosted_rls_summary.py"',
        "Phase 6Q hosted RLS evidence independently verified.",
    ):
        assert marker in script

    assert "SUPABASE_SECRET_KEY" not in script
    assert "SUPABASE_SERVICE_ROLE_KEY" not in script
    assert "global_terminal_hosted_scheduler_control" not in script
    assert "Write-Host $email" not in script


def test_phase6q_hosted_rls_handoff_parses_in_windows_powershell():
    command = (
        "$errors=$null; "
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "(Resolve-Path 'scripts/test-phase6q-hosted-scheduler-rls.ps1'),"
        "[ref]$null,[ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { $errors | ForEach-Object { $_.Message }; exit 1 }"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def _hosted_rls_summary(now: datetime) -> dict[str, object]:
    return {
        "evidence_version": "phase6q.hosted-rls.v1",
        "captured_at": now.isoformat(),
        "passed": True,
        "remote_schema_verified": True,
        "account_identities_distinct": True,
        "tenant_scopes_distinct": True,
        "cross_tenant_schedule_rows_visible": 0,
        "cross_tenant_run_rows_visible": 0,
        "cross_tenant_audit_rows_visible": 0,
        "optimistic_conflict_verified": True,
        "immutable_audit_verified": True,
        "deleted_schedule_replacement_verified": True,
        "original_account_document_restored": True,
        "operator_gate_changed": False,
        "hosted_worker_invoked": False,
        "hosted_scheduler_verified": False,
        "provider_call_count": 0,
        "identifiers_redacted": True,
        "secrets_printed": False,
    }


def test_phase6q_hosted_rls_summary_verifier_accepts_fresh_redacted_evidence():
    now = datetime(2026, 7, 28, 9, tzinfo=timezone.utc)
    result = validate_phase6q_hosted_rls_summary(_hosted_rls_summary(now), now=now)

    assert result["passed"] is True
    assert result["reasons"] == []
    assert result["provider_call_count"] == 0
    assert result["hosted_scheduler_verified"] is False


def test_phase6q_hosted_rls_summary_verifier_fails_closed_on_leak_promotion_and_expiry():
    now = datetime(2026, 7, 28, 9, tzinfo=timezone.utc)
    payload = _hosted_rls_summary(now - timedelta(hours=169))
    payload["hosted_scheduler_verified"] = True
    payload["account_email"] = "must-not-be-present@example.test"
    payload["provider_call_count"] = 1

    result = validate_phase6q_hosted_rls_summary(payload, now=now)

    assert result["passed"] is False
    assert set(result["reasons"]) >= {
        "unexpected-fields-present",
        "hosted-scheduler-verification-promoted",
        "provider_call_count-not-zero",
        "evidence-expired",
    }


def test_phase6q_preflight_requires_and_recognizes_fresh_hosted_rls_evidence(tmp_path: Path):
    review = tmp_path / "review_workspace"
    review.mkdir()
    now = datetime.now(timezone.utc)
    (review / "phase6q_hosted_rls_summary.json").write_text(
        json.dumps(_hosted_rls_summary(now)),
        encoding="utf-8",
    )

    result = build_preflight(tmp_path)

    assert result["checks"]["hosted_rls_verified"] is True
    assert "hosted_rls_verified-missing" not in result["blockers"]
