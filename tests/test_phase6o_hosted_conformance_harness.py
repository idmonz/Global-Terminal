from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOSTED = ROOT / "scripts" / "test-phase6o-alert-rls.ps1"


def _configured_private_values() -> list[str]:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return []

    names = {
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "SUPABASE_ANON_KEY",
        "PHASE6M_TEST_ACCOUNT_A_EMAIL",
        "PHASE6M_TEST_ACCOUNT_B_EMAIL",
        "PHASE6M_TEST_ACCOUNT_A_USER_ID",
        "PHASE6M_TEST_ACCOUNT_B_USER_ID",
        "PHASE6M_TEST_ACCOUNT_A_TENANT_ID",
        "PHASE6M_TEST_ACCOUNT_B_TENANT_ID",
    }
    configured: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() in names:
            configured[name.strip()] = value.strip().strip("\"'")
    return [value for value in configured.values() if len(value) >= 8]


def test_phase6o_hosted_harness_is_password_and_token_safe():
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

    assert 'read-host "$accountlabel password" -assecurestring' in script
    assert "service_role" not in script
    assert "supabase_secret_key" not in script
    assert "access_token  =" not in script
    assert "identifiers_redacted = $true" in script
    assert "secrets_printed = $false" in script
    for forbidden in _configured_private_values():
        assert forbidden.lower() not in script


def test_phase6o_hosted_harness_covers_rls_integrity_recovery_and_cleanup():
    script = HOSTED.read_text(encoding="utf-8").lower()

    for table in (
        "global_terminal_watchlist_alert_rules",
        "global_terminal_watchlist_alert_evaluations",
        "global_terminal_watchlist_alert_triggers",
        "global_terminal_watchlist_alert_audit",
        "global_terminal_watchlist_alert_worker_state",
    ):
        assert table in script

    for marker in (
        "account b cannot read account a row",
        "account b cannot insert an alert rule into account a tenant",
        "composite foreign keys block account b",
        "authenticated clients cannot forge alert manager audit rows",
        "stale optimistic rule update changes zero rows",
        "account a records a disabled worker restart state",
        "alert manager audit evidence survives parent deletion",
        "retained alert manager audit evidence remains isolated from account b",
    ):
        assert marker in script

    assert 'evidence_version = "phase6o.hosted.rls.v1"' in script
    assert "hosted_persistence_verified = $true" in script
    assert "hosted_scheduler_verified = $false" in script
    assert "provider_calls = 0" in script
