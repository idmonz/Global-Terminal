from __future__ import annotations

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_phase6q_local_database_harness_covers_scheduler_security_and_recovery():
    sql = (ROOT / "supabase/tests/phase6q_hosted_scheduler_rls.integration.sql").read_text(encoding="utf-8")
    runner = (ROOT / "scripts/run_phase6q_local_db_conformance.ps1").read_text(encoding="utf-8")

    for marker in (
        "Account B can read Account A scheduler evidence",
        "Safe default did not block claim",
        "Active lease did not suppress overlap",
        "Account document replay was not deduplicated",
        "Terminal replay was not idempotent",
        "Provider failure replaced the last-known-good run",
        "Global kill switch did not block claim",
        "Authenticated direct schedule forge was accepted",
        "Immutable scheduler audit evidence is incomplete",
        "A deleted schedule blocked its bounded replacement",
        "hsched_phase6q_replacement",
        "PHASE6Q_LOCAL_CONFORMANCE_PASS",
        "rollback;",
    ):
        assert marker in sql
    assert "docker exec -i" in runner
    assert "ON_ERROR_STOP=1" in runner
    assert "[REDACTED]" in runner


def test_phase6q_visual_harness_is_machine_verifiable_and_zero_call():
    package = (ROOT / "apps/web/package.json").read_text(encoding="utf-8")
    capture = (ROOT / "apps/web/scripts/capture-phase6q.mjs").read_text(encoding="utf-8")
    verifier = (ROOT / "apps/web/scripts/verify-phase6q-visual-summary.mjs").read_text(encoding="utf-8")
    handoff = (ROOT / "scripts/run_phase6q_visual_handoff.ps1").read_text(encoding="utf-8")

    assert '"visual:phase6q": "node scripts/capture-phase6q.mjs"' in package
    assert '"visual:verify:phase6q": "node scripts/verify-phase6q-visual-summary.mjs"' in package
    for marker in (
        "phase6q.visual.v1",
        "hosted-schedule-safe-default-desktop",
        "hosted-schedule-enabled-unverified-desktop",
        "hosted-schedule-partial-lkg-desktop",
        "hosted-schedule-completed-source-desktop",
        "hosted-schedule-quota-blocked-desktop",
        "hosted-schedule-provider-offline-desktop",
        "hosted-schedule-lease-expired-desktop",
        "hosted-schedule-recovered-desktop",
        "hosted-schedule-account-b-isolated-desktop",
        "hosted-schedule-session-expired-desktop",
        "phase6q-regression-${name}",
        "hosted-schedule-killed-desktop",
        "hosted-schedule-mobile-390x844",
        "providerRequestCount",
        "horizontalOverflow",
        "unlabeledControls",
        "inspectFocus",
        "assertCleanTelemetry",
    ):
        assert marker in capture
    assert '["analyst", "/?view=analyst-workspace' in capture
    assert "provider_request_count" in verifier
    assert "hosted-unverified" in verifier
    assert "npm --prefix apps/web run visual:phase6q" in handoff
    assert "npm --prefix apps/web run visual:verify:phase6q" in handoff
    assert "scripts/start_local_product.py --production" in handoff


def test_phase6q_performance_harness_is_bounded_and_redacted():
    benchmark = (ROOT / "scripts/benchmark_phase6q.py").read_text(encoding="utf-8")
    for marker in (
        "phase6q.performance.v1",
        "sample_count",
        "limit_p95_ms",
        "provider_call_count",
        "identifiers_redacted",
        "secrets_printed",
        "TemporaryDirectory",
    ):
        assert marker in benchmark


def test_phase6q_hosted_evidence_verifier_is_independent_and_redacted():
    verifier = (ROOT / "scripts/verify_phase6q_hosted_evidence.py").read_text(encoding="utf-8")
    operations = (ROOT / "lib/hosted_scheduler_operations.py").read_text(encoding="utf-8")
    for marker in (
        "phase6q.hosted.handoff.v1",
        "deployed_invocation",
        "job_history_observed",
        "tenant_source_backed_result",
        "account_isolation",
        "overlap_suppressed",
        "quota_bounded",
        "provider_failure_preserved_lkg",
        "kill_switch",
        "lease_recovery",
        "cleanup",
        "zero_read_provider_calls",
        "private-value-pattern-present",
    ):
        assert marker in operations
    assert "without printing its payload" in verifier
    assert "validate_hosted_scheduler_evidence" in verifier


def test_phase6q_deployment_preflight_is_read_only_and_secret_safe(tmp_path: Path):
    from scripts.preflight_phase6q_hosted_deployment import build_preflight

    (tmp_path / ".env").write_text(
        "SUPABASE_SECRET_KEY=sb_secret_should_never_be_printed\n"
        "ALPHAVANTAGE_API_KEY=alpha_private_value\n"
        "FINNHUB_API_KEY=finnhub_private_value\n",
        encoding="utf-8",
    )
    result = build_preflight(tmp_path)
    encoded = json.dumps(result)
    assert result["preflight_completed"] is True
    assert result["deployment_ready"] is False
    assert result["hosted_scheduler_verified"] is False
    assert result["provider_call_count"] == 0
    assert result["remote_mutation"] is False
    assert "sb_secret_should_never_be_printed" not in encoded
    assert "alpha_private_value" not in encoded
    assert "finnhub_private_value" not in encoded


def test_phase6q_owner_handoff_documents_new_supabase_key_and_default_branch_boundary():
    preflight = (ROOT / "scripts/preflight_phase6q_hosted_deployment.py").read_text(encoding="utf-8")
    wrapper = (ROOT / "scripts/run_phase6q_hosted_preflight.ps1").read_text(encoding="utf-8")
    handoff = (ROOT / "docs/PHASE_6Q_HOSTED_DEPLOYMENT_HANDOFF.md").read_text(encoding="utf-8")
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for marker in (
        "phase6q.hosted.preflight.v1",
        "remote_mutation",
        "provider_call_count",
        "github_environment_secrets_verified",
        "remote_migration_applied",
        "workflow_hardening_valid",
        "hosted_rls_verified",
        "quality_workflow_deployed",
        "supply_chain_policy_committed",
    ):
        assert marker in preflight
    assert "prints no key" in wrapper
    for version in ("20260727143000", "20260727190000", "20260727191500"):
        assert version in handoff
    assert "test-phase6q-hosted-scheduler-rls.ps1" in handoff
    assert "SecureString" in handoff
    assert "sb_secret_*" in handoff
    assert "default branch" in handoff
    assert "Quality gate" in handoff
    assert "verify_phase6q_hosted_evidence.py" in handoff
    for marker in ("external (2)/", "review_workspace/", "supabase/.temp/", "apps/web/node_modules/"):
        assert marker in ignore
