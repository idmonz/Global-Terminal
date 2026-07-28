from pathlib import Path


def test_phase6o_supabase_migration_has_rls_least_privilege_and_composite_integrity():
    root = Path(__file__).resolve().parents[1]
    sql = (root / "supabase/migrations/20260715120000_phase6o_watchlist_alert_manager.sql").read_text(encoding="utf-8").lower()

    for table in (
        "global_terminal_watchlist_alert_rules",
        "global_terminal_watchlist_alert_evaluations",
        "global_terminal_watchlist_alert_triggers",
        "global_terminal_watchlist_alert_audit",
        "global_terminal_watchlist_alert_worker_state",
    ):
        assert f"alter table public.{table} enable row level security" in sql
        assert f"revoke all on table public.{table} from anon, authenticated" in sql
    assert "foreign key (tenant_id, owner_user_id, snapshot_id)" in sql
    assert "foreign key (tenant_id, owner_user_id, rule_id)" in sql
    assert "grant select on table public.global_terminal_watchlist_alert_audit" in sql
    assert "grant select, insert" not in sql.split("grant select on table public.global_terminal_watchlist_alert_audit", 1)[1].split(";", 1)[0]
    assert "security definer" in sql
    assert "set search_path = ''" in sql
    assert "service_role" not in sql
    assert "auth.uid()" in sql


def test_phase6o_has_executable_local_rls_harness():
    root = Path(__file__).resolve().parents[1]
    sql = (root / "supabase/tests/phase6o_alert_manager_rls.integration.sql").read_text(encoding="utf-8").lower()
    runner = (root / "scripts/test-phase6o-local-alert-rls.ps1").read_text(encoding="utf-8").lower()

    for marker in (
        "set local role authenticated",
        "request.jwt.claim.sub",
        "cross-tenant rule insert unexpectedly succeeded",
        "cross-tenant alert parent linkage unexpectedly succeeded",
        "stale optimistic rule update changed a row",
        "alert audit evidence did not survive parent deletion",
        "account b can see account a retained alert audit evidence",
        "rollback",
    ):
        assert marker in sql
    assert "docker exec -i" in runner
    assert "phase 6o local alert manager isolation checks passed" in runner


def test_phase6o_has_secret_safe_anonymous_denial_harness():
    root = Path(__file__).resolve().parents[1]
    runner = (root / "scripts/test-phase6o-anonymous-denial.ps1").read_text(encoding="utf-8").lower()

    assert "supabase_publishable_key" in runner
    assert "statuscode -notin @(401, 403)" in runner
    assert "response bodies are not printed" in runner
    assert "phase 6o anonymous denial passed" in runner
