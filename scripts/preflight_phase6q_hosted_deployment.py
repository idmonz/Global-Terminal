from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_github_workflows import validate_workflows
from scripts.verify_phase6q_hosted_rls_summary import verify_file as verify_hosted_rls_file


MIGRATION_VERSIONS = {
    "20260727143000",
    "20260727190000",
    "20260727191500",
}
WORKFLOW_PATH = ".github/workflows/phase6q-hosted-observation.yml"
QUALITY_WORKFLOW_PATH = ".github/workflows/quality-gate.yml"
HOSTED_RLS_SUMMARY_PATH = "review_workspace/phase6q_hosted_rls_summary.json"
SUPPLY_CHAIN_PATHS = {
    QUALITY_WORKFLOW_PATH,
    ".github/action-pins.json",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/SECURITY.md",
}
REQUIRED_GITHUB_SECRETS = {
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "ALPHAVANTAGE_API_KEY",
    "FINNHUB_API_KEY",
}


def _dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _run(command: list[str], *, cwd: Path, timeout: int = 45) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 124, ""
    stdout = str(completed.stdout or "")
    stderr = str(completed.stderr or "")
    # Supabase CLI writes the migration table to stderr on some Windows builds.
    # Prefer stdout for JSON-producing commands such as `gh`, then fall back to
    # stderr so the linked migration probe does not report a false negative.
    return int(completed.returncode), stdout if stdout.strip() else stderr


def _migration_is_remote(output: str) -> bool:
    aligned: set[str] = set()
    try:
        payload = json.loads(output)
    except (TypeError, ValueError):
        payload = {}
    rows = payload.get("migrations") if isinstance(payload, dict) else None
    if isinstance(rows, list):
        aligned.update(
            str(row.get("local") or "")
            for row in rows
            if isinstance(row, dict)
            and str(row.get("local") or "") in MIGRATION_VERSIONS
            and str(row.get("local") or "") == str(row.get("remote") or "")
        )
    for line in output.splitlines():
        if "|" not in line:
            continue
        columns = [column.strip().strip("`") for column in line.split("|")]
        if len(columns) >= 2 and columns[0] in MIGRATION_VERSIONS and columns[0] == columns[1]:
            aligned.add(columns[0])
    return aligned == MIGRATION_VERSIONS


def _workflow_is_bounded(path: Path) -> bool:
    if not path.exists():
        return False
    body = path.read_text(encoding="utf-8")
    required = (
        'cron: "17 * * * *"',
        "cancel-in-progress: false",
        "permissions:\n  contents: read",
        "timeout-minutes: 4",
        "environment: phase6q-pilot",
        "python scripts/run_phase6q_hosted_scheduler.py",
    )
    return all(marker in body for marker in required)


def build_preflight(
    root: Path = ROOT,
    *,
    probe_linked: bool = False,
    probe_github: bool = False,
) -> dict[str, Any]:
    env = _dotenv(root / ".env")
    migration_present = all(
        any((root / "supabase/migrations").glob(f"{version}_*.sql"))
        for version in MIGRATION_VERSIONS
    )
    linked = (root / "supabase/.temp/project-ref").exists()
    workflow_path = root / WORKFLOW_PATH
    workflow_bounded = _workflow_is_bounded(workflow_path)
    workflow_security = validate_workflows(root)
    workflow_hardening_valid = bool(workflow_security.get("ok"))
    hosted_rls_result = verify_hosted_rls_file(root / HOSTED_RLS_SUMMARY_PATH)
    hosted_rls_verified = bool(hosted_rls_result.get("passed"))

    git_available = shutil.which("git") is not None
    commit_present = False
    remote_present = False
    local_remote_synced = False
    workflow_committed = False
    supply_chain_policy_committed = False
    if git_available:
        head_code, local_head = _run(["git", "rev-parse", "--verify", "HEAD"], cwd=root, timeout=10)
        commit_present = head_code == 0
        remote_present = _run(["git", "remote", "get-url", "origin"], cwd=root, timeout=10)[0] == 0
        upstream_code, upstream_head = _run(["git", "rev-parse", "@{upstream}"], cwd=root, timeout=10)
        local_remote_synced = (
            commit_present
            and remote_present
            and upstream_code == 0
            and bool(local_head.strip())
            and local_head.strip() == upstream_head.strip()
        )
        workflow_committed = _run(["git", "ls-files", "--error-unmatch", WORKFLOW_PATH], cwd=root, timeout=10)[0] == 0
        supply_chain_policy_committed = all(
            _run(["git", "ls-files", "--error-unmatch", path], cwd=root, timeout=10)[0] == 0
            for path in SUPPLY_CHAIN_PATHS
        )

    supabase_cli_available = shutil.which("supabase") is not None
    remote_probe_status = "not-requested"
    remote_migration_applied = False
    if probe_linked:
        if not supabase_cli_available:
            remote_probe_status = "cli-missing"
        elif not linked:
            remote_probe_status = "not-linked"
        else:
            code, output = _run(["supabase", "migration", "list", "--linked"], cwd=root)
            remote_migration_applied = code == 0 and _migration_is_remote(output)
            remote_probe_status = "reachable" if code == 0 else "unreachable"

    gh_available = shutil.which("gh") is not None
    github_authenticated = False
    github_repository_private = False
    github_default_branch_main = False
    github_main_branch_protected = False
    workflow_deployed = False
    quality_workflow_deployed = False
    quality_workflow_passed = False
    github_secrets_verified = False
    github_probe_status = "not-requested"
    if probe_github:
        if not gh_available:
            github_probe_status = "cli-missing"
        elif not remote_present:
            github_probe_status = "remote-missing"
        else:
            github_authenticated = _run(["gh", "auth", "status"], cwd=root, timeout=20)[0] == 0
            if github_authenticated:
                repo_code, repo_output = _run(
                    ["gh", "repo", "view", "--json", "nameWithOwner,isPrivate,defaultBranchRef"],
                    cwd=root,
                    timeout=30,
                )
                try:
                    repository = json.loads(repo_output) if repo_code == 0 else {}
                except ValueError:
                    repository = {}
                github_repository_private = repository.get("isPrivate") is True
                default_branch = repository.get("defaultBranchRef")
                github_default_branch_main = (
                    isinstance(default_branch, dict)
                    and default_branch.get("name") == "main"
                )
                repository_name = str(repository.get("nameWithOwner") or "").strip()
                if repository_name and github_default_branch_main:
                    protection_code, protection_output = _run(
                        [
                            "gh",
                            "api",
                            f"repos/{repository_name}/branches/main",
                            "--jq",
                            ".protected",
                        ],
                        cwd=root,
                        timeout=30,
                    )
                    github_main_branch_protected = (
                        protection_code == 0
                        and protection_output.strip().lower() == "true"
                    )
                workflow_code, workflow_output = _run(
                    ["gh", "workflow", "view", "phase6q-hosted-observation.yml", "--json", "state,path"],
                    cwd=root,
                    timeout=30,
                )
                try:
                    workflow = json.loads(workflow_output) if workflow_code == 0 else {}
                except ValueError:
                    workflow = {}
                workflow_deployed = workflow.get("state") == "active" and workflow.get("path") == WORKFLOW_PATH
                quality_code, quality_output = _run(
                    ["gh", "workflow", "view", "quality-gate.yml", "--json", "state,path"],
                    cwd=root,
                    timeout=30,
                )
                try:
                    quality_workflow = json.loads(quality_output) if quality_code == 0 else {}
                except ValueError:
                    quality_workflow = {}
                quality_workflow_deployed = (
                    quality_workflow.get("state") == "active"
                    and quality_workflow.get("path") == QUALITY_WORKFLOW_PATH
                )
                run_code, run_output = _run(
                    [
                        "gh",
                        "run",
                        "list",
                        "--workflow",
                        "quality-gate.yml",
                        "--branch",
                        "main",
                        "--limit",
                        "20",
                        "--json",
                        "status,conclusion,headSha",
                    ],
                    cwd=root,
                    timeout=30,
                )
                try:
                    quality_runs = json.loads(run_output) if run_code == 0 else []
                except ValueError:
                    quality_runs = []
                quality_workflow_passed = any(
                    isinstance(row, dict)
                    and row.get("status") == "completed"
                    and row.get("conclusion") == "success"
                    and str(row.get("headSha") or "").strip() == local_head.strip()
                    for row in quality_runs
                )
                secret_code, secret_output = _run(
                    ["gh", "secret", "list", "--env", "phase6q-pilot", "--json", "name"],
                    cwd=root,
                    timeout=30,
                )
                try:
                    names = {str(row.get("name") or "") for row in json.loads(secret_output)} if secret_code == 0 else set()
                except (TypeError, ValueError):
                    names = set()
                github_secrets_verified = REQUIRED_GITHUB_SECRETS <= names
                github_probe_status = "reachable"
            else:
                github_probe_status = "not-authenticated"

    local_secret_configured = bool(env.get("SUPABASE_SECRET_KEY") or env.get("SUPABASE_SERVICE_ROLE_KEY"))
    local_provider_keys_configured = bool(env.get("ALPHAVANTAGE_API_KEY") and env.get("FINNHUB_API_KEY"))
    safe_local_gate = (
        env.get("GLOBAL_TERMINAL_HOSTED_SCHEDULER_ENABLED", "false").lower() != "true"
        and env.get("GLOBAL_TERMINAL_HOSTED_SCHEDULER_KILL_SWITCH", "true").lower() == "true"
        and env.get("GLOBAL_TERMINAL_HOSTED_SCHEDULER_VERIFIED", "false").lower() != "true"
    )

    checks = {
        "migration_present": migration_present,
        "supabase_linked": linked,
        "remote_migration_applied": remote_migration_applied,
        "workflow_bounded": workflow_bounded,
        "workflow_hardening_valid": workflow_hardening_valid,
        "hosted_rls_verified": hosted_rls_verified,
        "git_commit_present": commit_present,
        "git_remote_present": remote_present,
        "local_remote_synced": local_remote_synced,
        "workflow_committed": workflow_committed,
        "supply_chain_policy_committed": supply_chain_policy_committed,
        "github_authenticated": github_authenticated,
        "github_repository_private": github_repository_private,
        "github_default_branch_main": github_default_branch_main,
        "github_main_branch_protected": github_main_branch_protected,
        "workflow_deployed": workflow_deployed,
        "quality_workflow_deployed": quality_workflow_deployed,
        "quality_workflow_passed": quality_workflow_passed,
        "github_environment_secrets_verified": github_secrets_verified,
        "local_service_secret_configured": local_secret_configured,
        "local_provider_keys_configured": local_provider_keys_configured,
        "safe_local_gate": safe_local_gate,
    }
    required_for_deployment = (
        "migration_present",
        "supabase_linked",
        "remote_migration_applied",
        "workflow_bounded",
        "workflow_hardening_valid",
        "hosted_rls_verified",
        "git_commit_present",
        "git_remote_present",
        "local_remote_synced",
        "workflow_committed",
        "supply_chain_policy_committed",
        "github_authenticated",
        "github_repository_private",
        "github_default_branch_main",
        "github_main_branch_protected",
        "workflow_deployed",
        "quality_workflow_deployed",
        "quality_workflow_passed",
        "github_environment_secrets_verified",
        "safe_local_gate",
    )
    blockers = [f"{name}-missing" for name in required_for_deployment if not checks[name]]
    if remote_probe_status == "not-requested":
        blockers.append("linked-migration-not-probed")
    if github_probe_status == "not-requested":
        blockers.append("github-deployment-not-probed")

    return {
        "evidence_version": "phase6q.hosted.preflight.v1",
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "preflight_completed": True,
        "deployment_ready": not blockers,
        "hosted_scheduler_verified": False,
        "runner_kind": "github-actions-python",
        "remote_probe_status": remote_probe_status,
        "github_probe_status": github_probe_status,
        "checks": checks,
        "blockers": sorted(set(blockers)),
        "provider_call_count": 0,
        "remote_mutation": False,
        "identifiers_redacted": True,
        "secrets_printed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a read-only, redacted Phase 6Q hosted deployment preflight.")
    parser.add_argument("--probe-linked", action="store_true")
    parser.add_argument("--probe-github", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", default="review_workspace/phase6q_hosted_deployment_preflight_summary.json")
    args = parser.parse_args()
    result = build_preflight(ROOT, probe_linked=args.probe_linked, probe_github=args.probe_github)
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if args.strict and not result["deployment_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
