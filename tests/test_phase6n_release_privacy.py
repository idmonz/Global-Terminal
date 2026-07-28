from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PRIVATE_ENV_NAMES = (
    "SUPABASE_URL",
    "SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_ANON_KEY",
    "PHASE6M_TEST_ACCOUNT_A_EMAIL",
    "PHASE6M_TEST_ACCOUNT_B_EMAIL",
    "PHASE6M_TEST_ACCOUNT_A_USER_ID",
    "PHASE6M_TEST_ACCOUNT_B_USER_ID",
    "PHASE6M_TEST_ACCOUNT_A_TENANT_ID",
    "PHASE6M_TEST_ACCOUNT_B_TENANT_ID",
)


def _configured_private_values() -> list[str]:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return []

    configured: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        configured[name.strip()] = value.strip().strip("\"'")
    return [
        configured[name]
        for name in PRIVATE_ENV_NAMES
        if len(configured.get(name, "")) >= 8
    ]


def test_phase6n_hosted_evidence_and_scripts_do_not_embed_test_identity_values():
    paths = (
        ROOT / "docs/PHASE_6M_HOSTED_CONFORMANCE_EVIDENCE.md",
        ROOT / "docs/PHASE_6N_SECURITY_AND_PRIVACY_REPORT.md",
        ROOT / "scripts/bootstrap-phase6m-users.ps1",
        ROOT / "scripts/test-phase6m-rls-crud.ps1",
        ROOT / "scripts/test-phase6n-observation-rls.ps1",
        ROOT / "scripts/test-phase6n-local-rls.ps1",
        ROOT / "scripts/test-phase6o-alert-rls.ps1",
        ROOT / "supabase/tests/phase6n_observation_rls.integration.sql",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()

    for forbidden in _configured_private_values():
        assert forbidden not in combined
    assert "phase6m_test_account_a_email" in combined
    assert "phase6m_test_account_b_tenant_id" in combined
