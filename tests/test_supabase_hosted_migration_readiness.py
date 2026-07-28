from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIR = ROOT / "supabase" / "migrations"
PHASE6N = MIGRATION_DIR / "20260714230000_phase6n_observation_and_hosted_hardening.sql"


def test_supabase_migration_versions_are_unique_and_cli_safe():
    migrations = sorted(MIGRATION_DIR.glob("*.sql"))
    versions = []
    for migration in migrations:
        match = re.fullmatch(r"(\d{14})_[a-z0-9_]+\.sql", migration.name)
        assert match, f"Migration does not use a 14-digit version: {migration.name}"
        versions.append(match.group(1))

    assert len(versions) == len(set(versions))
    assert versions == sorted(versions)


def test_phase6n_hosted_migration_enforces_tenant_and_parent_integrity():
    sql = PHASE6N.read_text(encoding="utf-8").lower()

    assert sql.startswith("begin;")
    assert sql.rstrip().endswith("commit;")
    assert sql.count("references public.global_terminal_tenants(id)") == 4
    assert sql.count("foreign key (tenant_id, owner_user_id, run_id)") == 2
    assert "global_terminal_tenant_memberships" in sql
    assert "owner_user_id = (select auth.uid())" in sql
    assert "membership.role in ('owner', 'member')" in sql


def test_phase6n_hosted_migration_is_least_privilege_and_audited():
    sql = PHASE6N.read_text(encoding="utf-8").lower()

    for table in (
        "global_terminal_observation_runs",
        "global_terminal_observation_snapshots",
        "global_terminal_provider_quota_ledger",
        "global_terminal_observation_run_audit",
    ):
        assert f"revoke all on table public.{table} from anon, authenticated" in sql
        assert f"alter table public.{table} enable row level security" in sql

    assert "grant select on table public.global_terminal_observation_run_audit" in sql
    assert "grant select, insert on table public.global_terminal_provider_quota_ledger" in sql
    assert "global_terminal_record_observation_run_audit" in sql
    assert "after insert or update or delete" in sql
    assert "revoke all on function public.global_terminal_record_observation_run_audit()" in sql
    assert "references public.global_terminal_observation_runs(run_id)" not in sql


def test_phase6n_hardening_revokes_historical_anon_table_access():
    sql = PHASE6N.read_text(encoding="utf-8").lower()

    expected = {
        "global_terminal_tenants",
        "global_terminal_tenant_memberships",
        "global_terminal_workspace_preferences",
        "global_terminal_watchlists",
        "global_terminal_watchlist_items",
        "global_terminal_import_receipts",
        "global_terminal_alert_rules",
        "global_terminal_inbox_items",
        "global_terminal_sync_receipts",
        "global_terminal_deletion_tombstones",
        "global_terminal_attention_states",
        "global_terminal_attention_policies",
        "global_terminal_attention_checkpoints",
        "global_terminal_attention_audit",
    }
    for table in expected:
        assert f"'{table}'" in sql
    assert "revoke all on table public.%i from anon" in sql
