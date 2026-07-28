from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOSTED = ROOT / "scripts" / "test-phase6n-observation-rls.ps1"
LOCAL = ROOT / "scripts" / "test-phase6n-local-rls.ps1"
LOCAL_SQL = ROOT / "supabase" / "tests" / "phase6n_observation_rls.integration.sql"


def test_phase6n_hosted_harness_is_token_safe_and_complete():
    script = HOSTED.read_text(encoding="utf-8").lower()

    for name in (
        "phase6m_test_account_a_email",
        "phase6m_test_account_b_email",
        "phase6m_test_account_a_user_id",
        "phase6m_test_account_b_user_id",
        "phase6m_test_account_a_tenant_id",
        "phase6m_test_account_b_tenant_id",
    ):
        assert name in script

    for table in (
        "global_terminal_observation_runs",
        "global_terminal_observation_snapshots",
        "global_terminal_provider_quota_ledger",
        "global_terminal_observation_run_audit",
    ):
        assert table in script

    assert "read-host \"$accountlabel password\" -assecurestring" in script
    assert "service_role" not in script
    assert "supabase_secret_key" not in script
    assert "access_token  =" not in script
    assert "secrets_printed = $false" in script
    assert "optimistic_conflict = $true" in script
    assert "provider_calls = 0" in script


def test_phase6n_local_harness_proves_real_rls_paths_without_persistence():
    runner = LOCAL.read_text(encoding="utf-8").lower()
    sql = LOCAL_SQL.read_text(encoding="utf-8").lower()

    assert "docker exec -i" in runner
    assert "phase6n_observation_rls.integration.sql" in runner
    assert sql.startswith("\\set on_error_stop on")
    assert "set local role authenticated" in sql
    assert "cross-tenant run insert unexpectedly succeeded" in sql
    assert "authenticated audit mutation unexpectedly succeeded" in sql
    assert "stale optimistic update unexpectedly changed a row" in sql
    assert "audit evidence did not survive run deletion" in sql
    assert "rollback;" in sql
    assert "phase6n_local_rls_pass" in sql
