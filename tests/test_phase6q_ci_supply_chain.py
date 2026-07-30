from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import scripts.preflight_phase6q_hosted_deployment as deployment_preflight
from scripts.preflight_phase6q_hosted_deployment import build_preflight
from scripts.validate_github_workflows import validate_workflows
from scripts.verify_phase6q_remote_anonymous_denial import verify_remote_anonymous_denial


ROOT = Path(__file__).resolve().parents[1]


def test_phase6q_github_workflows_are_pinned_bounded_and_secret_separated():
    result = validate_workflows(ROOT)

    assert result["ok"] is True, result["errors"]
    assert result["workflow_count"] == 2
    assert result["action_use_count"] == 7
    assert result["reviewed_action_count"] == 3
    assert result["quality_gate_secret_count"] == 0
    assert result["scheduler_secret_name_count"] == 4
    assert result["provider_call_count"] == 0
    assert result["secrets_printed"] is False


def test_phase6q_workflow_validator_rejects_mutable_action_and_quality_secret(tmp_path: Path):
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    quality = tmp_path / ".github/workflows/quality-gate.yml"
    body = quality.read_text(encoding="utf-8")
    body = body.replace(
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
        "actions/checkout@v7",
        1,
    )
    body += "\n# forbidden probe: ${{ secrets.SUPABASE_SECRET_KEY }}\n"
    quality.write_text(body, encoding="utf-8")

    result = validate_workflows(tmp_path)

    assert result["ok"] is False
    assert any(error.startswith("mutable-action-reference:") for error in result["errors"])
    assert "quality-gate-secret-use-forbidden" in result["errors"]


def test_phase6q_workflow_validator_rejects_scheduler_without_operator_gate(tmp_path: Path):
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    scheduler = tmp_path / ".github/workflows/phase6q-hosted-observation.yml"
    body = scheduler.read_text(encoding="utf-8")
    body = body.replace("vars.GLOBAL_TERMINAL_HOSTED_SCHEDULER_OPERATOR_ENABLED == 'true'", "true", 1)
    scheduler.write_text(body, encoding="utf-8")

    result = validate_workflows(tmp_path)

    assert result["ok"] is False
    assert "scheduler-hardening-marker-missing:vars.GLOBAL_TERMINAL_HOSTED_SCHEDULER_OPERATOR_ENABLED == 'true'" in result["errors"]


def test_phase6q_workflow_validator_rejects_privilege_unknown_action_and_missing_timeout(tmp_path: Path):
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    quality = tmp_path / ".github/workflows/quality-gate.yml"
    body = quality.read_text(encoding="utf-8")
    body = body.replace("  pull_request:\n", "  pull_request_target:\n", 1)
    body = body.replace("  contents: read\n", "  contents: write\n", 1)
    body = body.replace("    timeout-minutes: 25\n", "", 1)
    body += "\n# rejected action\n- uses: example/unreviewed@" + ("a" * 40) + " # v1\n"
    quality.write_text(body, encoding="utf-8")

    result = validate_workflows(tmp_path)

    assert result["ok"] is False
    assert ".github/workflows/quality-gate.yml" in " ".join(result["errors"])
    assert any(error.startswith("pull-request-target-forbidden:") for error in result["errors"])
    assert any(error.startswith("write-permission-forbidden:") for error in result["errors"])
    assert any(error.startswith("job-timeout-missing:") for error in result["errors"])
    assert any(error.startswith("unreviewed-action:") for error in result["errors"])


def test_phase6q_action_pin_registry_matches_current_official_release_evidence():
    payload = json.loads((ROOT / ".github/action-pins.json").read_text(encoding="utf-8"))

    assert payload["evidence_version"] == "phase6q.action-pins.v1"
    assert payload["verified_at"] == "2026-07-27"
    assert payload["actions"] == {
        "actions/checkout": {
            "version": "v7.0.1",
            "sha": "3d3c42e5aac5ba805825da76410c181273ba90b1",
            "source_url": "https://github.com/actions/checkout/releases/tag/v7.0.1",
        },
        "actions/setup-python": {
            "version": "v7.0.0",
            "sha": "5fda3b95a4ea91299a34e894583c3862153e4b97",
            "source_url": "https://github.com/actions/setup-python/releases/tag/v7.0.0",
        },
        "actions/setup-node": {
            "version": "v7.0.0",
            "sha": "820762786026740c76f36085b0efc47a31fe5020",
            "source_url": "https://github.com/actions/setup-node/releases/tag/v7.0.0",
        },
    }


def test_phase6q_preflight_promotes_local_workflow_hardening_without_promoting_hosted_state():
    result = build_preflight(ROOT)

    assert result["checks"]["workflow_hardening_valid"] is True
    assert result["deployment_ready"] is False
    assert result["hosted_scheduler_verified"] is False
    assert result["provider_call_count"] == 0
    assert result["remote_mutation"] is False


def test_phase6q_preflight_requires_private_synced_main_and_current_quality_run(tmp_path: Path, monkeypatch):
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    migrations = tmp_path / "supabase/migrations"
    migrations.mkdir(parents=True)
    for version in deployment_preflight.MIGRATION_VERSIONS:
        (migrations / f"{version}_test.sql").write_text("select 1;\n", encoding="utf-8")
    linked = tmp_path / "supabase/.temp"
    linked.mkdir(parents=True)
    (linked / "project-ref").write_text("redacted\n", encoding="utf-8")
    review = tmp_path / "review_workspace"
    review.mkdir()
    (review / "phase6q_hosted_rls_summary.json").write_text(
        json.dumps(
            {
                "evidence_version": "phase6q.hosted-rls.v1",
                "captured_at": datetime.now(timezone.utc).isoformat(),
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
        ),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "ALPHAVANTAGE_API_KEY=alpha_test_value\n"
        "FINNHUB_API_KEY=finnhub_test_value\n"
        "GLOBAL_TERMINAL_HOSTED_SCHEDULER_ENABLED=false\n"
        "GLOBAL_TERMINAL_HOSTED_SCHEDULER_KILL_SWITCH=true\n"
        "GLOBAL_TERMINAL_HOSTED_SCHEDULER_VERIFIED=false\n",
        encoding="utf-8",
    )

    def fake_run(command: list[str], *, cwd: Path, timeout: int = 45):
        del cwd, timeout
        if command[:3] == ["git", "rev-parse", "--verify"]:
            return 0, "current-head\n"
        if command[:2] == ["git", "remote"]:
            return 0, "redacted-origin\n"
        if command[:2] == ["git", "rev-parse"]:
            return 0, "current-head\n"
        if command[:2] == ["git", "ls-files"]:
            return 0, "tracked\n"
        if command[:3] == ["supabase", "migration", "list"]:
            rows = "\n".join(f"`{version}` | `{version}` | `{version}`" for version in deployment_preflight.MIGRATION_VERSIONS)
            return 0, rows
        if command[:3] == ["gh", "auth", "status"]:
            return 0, "authenticated\n"
        if command[:3] == ["gh", "repo", "view"]:
            return 0, json.dumps(
                {
                    "nameWithOwner": "example/global-terminal",
                    "isPrivate": True,
                    "defaultBranchRef": {"name": "main"},
                }
            )
        if command[:2] == ["gh", "api"]:
            return 0, "true\n"
        if command[:3] == ["gh", "workflow", "view"]:
            path = deployment_preflight.WORKFLOW_PATH if "phase6q-hosted-observation.yml" in command else deployment_preflight.QUALITY_WORKFLOW_PATH
            return 0, json.dumps({"state": "active", "path": path})
        if command[:3] == ["gh", "run", "list"]:
            return 0, json.dumps([{"status": "completed", "conclusion": "success", "headSha": "current-head"}])
        if command[:3] == ["gh", "secret", "list"]:
            return 0, json.dumps([{"name": name} for name in deployment_preflight.REQUIRED_GITHUB_SECRETS])
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(deployment_preflight.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(deployment_preflight, "_run", fake_run)

    result = build_preflight(tmp_path, probe_linked=True, probe_github=True)

    assert result["deployment_ready"] is True
    assert result["blockers"] == []
    assert result["checks"]["local_remote_synced"] is True
    assert result["checks"]["github_repository_private"] is True
    assert result["checks"]["github_default_branch_main"] is True
    assert result["checks"]["github_main_branch_protected"] is True
    assert result["checks"]["quality_workflow_passed"] is True
    assert result["hosted_scheduler_verified"] is False


class _AnonymousProbeSession:
    def __init__(self, statuses: list[int]):
        self.statuses = iter(statuses)
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> SimpleNamespace:
        self.calls.append({"method": method, "url": url, "kwargs": kwargs})
        return SimpleNamespace(status_code=next(self.statuses))


def test_phase6q_remote_anonymous_probe_is_redacted_and_requires_every_denial(tmp_path: Path):
    (tmp_path / ".env").write_text(
        "SUPABASE_URL=https://project.example.test\nSUPABASE_PUBLISHABLE_KEY=publishable-private-value\n",
        encoding="utf-8",
    )
    session = _AnonymousProbeSession([401, 401, 403, 401, 403])

    result = verify_remote_anonymous_denial(tmp_path, requester=session)

    assert result["passed"] is True
    assert result["denied_count"] == result["expected_denied_count"] == 5
    assert result["provider_call_count"] == 0
    assert result["mutation_applied"] is False
    assert "publishable-private-value" not in json.dumps(result)
    assert len(session.calls) == 5


def test_phase6q_remote_anonymous_probe_fails_on_visible_surface(tmp_path: Path):
    (tmp_path / ".env").write_text(
        "SUPABASE_URL=https://project.example.test\nSUPABASE_PUBLISHABLE_KEY=publishable-private-value\n",
        encoding="utf-8",
    )

    result = verify_remote_anonymous_denial(
        tmp_path,
        requester=_AnonymousProbeSession([401, 200, 401, 401, 401]),
    )

    assert result["passed"] is False
    assert result["denied_count"] == 4
