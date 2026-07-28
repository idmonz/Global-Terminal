from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PIN_REGISTRY = ".github/action-pins.json"
QUALITY_WORKFLOW = ".github/workflows/quality-gate.yml"
SCHEDULER_WORKFLOW = ".github/workflows/phase6q-hosted-observation.yml"
DEPENDABOT_POLICY = ".github/dependabot.yml"
USES_PATTERN = re.compile(r"^\s*-?\s*uses:\s*([^@\s]+)@([^\s#]+)(?:\s*#\s*([^\s]+))?\s*$", re.MULTILINE)
SECRET_PATTERN = re.compile(r"\$\{\{\s*secrets\.([A-Z0-9_]+)\s*\}\}")
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_SCHEDULER_SECRETS = {
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "ALPHAVANTAGE_API_KEY",
    "FINNHUB_API_KEY",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _load_pins(root: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    path = root / PIN_REGISTRY
    if not path.exists():
        return {}, ["action-pin-registry-missing"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, ["action-pin-registry-invalid"]
    actions = payload.get("actions") if isinstance(payload, dict) else None
    if payload.get("evidence_version") != "phase6q.action-pins.v1" or not isinstance(actions, dict):
        return {}, ["action-pin-registry-contract-invalid"]
    normalized: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for name, value in actions.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            errors.append("action-pin-entry-invalid")
            continue
        version = str(value.get("version") or "")
        sha = str(value.get("sha") or "")
        source_url = str(value.get("source_url") or "")
        if not FULL_SHA_PATTERN.fullmatch(sha):
            errors.append(f"action-pin-sha-invalid:{name}")
        if not version.startswith("v") or source_url != f"https://github.com/{name}/releases/tag/{version}":
            errors.append(f"action-pin-evidence-invalid:{name}")
        normalized[name] = {"version": version, "sha": sha, "source_url": source_url}
    return normalized, errors


def _job_blocks(body: str) -> list[tuple[str, str]]:
    if "\njobs:\n" not in f"\n{body}":
        return []
    lines = body.splitlines()
    start = next((index for index, line in enumerate(lines) if line == "jobs:"), len(lines))
    indices = [index for index in range(start + 1, len(lines)) if re.fullmatch(r"  [A-Za-z0-9_-]+:", lines[index])]
    blocks: list[tuple[str, str]] = []
    for position, index in enumerate(indices):
        end = indices[position + 1] if position + 1 < len(indices) else len(lines)
        blocks.append((lines[index].strip().rstrip(":"), "\n".join(lines[index:end])))
    return blocks


def validate_workflows(root: Path = ROOT) -> dict[str, Any]:
    pins, errors = _load_pins(root)
    workflows_dir = root / ".github/workflows"
    workflow_paths = sorted((*workflows_dir.glob("*.yml"), *workflows_dir.glob("*.yaml"))) if workflows_dir.exists() else []
    if not workflow_paths:
        errors.append("workflow-directory-empty")

    action_uses = 0
    for path in workflow_paths:
        rel = path.relative_to(root).as_posix()
        body = _read(path)
        if "pull_request_target:" in body:
            errors.append(f"pull-request-target-forbidden:{rel}")
        if re.search(r"^\s*write-all\s*$|:\s*write\s*$", body, re.MULTILINE):
            errors.append(f"write-permission-forbidden:{rel}")
        if "permissions:\n  contents: read" not in body:
            errors.append(f"least-permission-missing:{rel}")
        if "concurrency:" not in body or "cancel-in-progress:" not in body:
            errors.append(f"concurrency-policy-missing:{rel}")
        jobs = _job_blocks(body)
        if not jobs:
            errors.append(f"jobs-missing:{rel}")
        for job, block in jobs:
            if "timeout-minutes:" not in block:
                errors.append(f"job-timeout-missing:{rel}:{job}")
        for action, reference, version_comment in USES_PATTERN.findall(body):
            action_uses += 1
            pin = pins.get(action)
            if not FULL_SHA_PATTERN.fullmatch(reference):
                errors.append(f"mutable-action-reference:{rel}:{action}")
            if pin is None:
                errors.append(f"unreviewed-action:{rel}:{action}")
                continue
            if reference != pin["sha"] or version_comment != pin["version"]:
                errors.append(f"action-pin-mismatch:{rel}:{action}")

    quality = _read(root / QUALITY_WORKFLOW)
    for marker in (
        "pull_request:",
        'branches: ["main"]',
        "python scripts/validate_github_workflows.py",
        "python scripts/validate_agent_harness.py",
        "python -m pytest -q",
        "python scripts/export_api_fixtures.py",
        "python scripts/build_release_zip.py",
        "python scripts/inspect_release_security.py",
        "npm ci",
        "npm test",
        "npm run lint",
        "npm run build",
        "npm audit --audit-level=high",
        "package-manager-cache: false",
        "persist-credentials: false",
    ):
        if marker not in quality:
            errors.append(f"quality-gate-marker-missing:{marker}")
    if SECRET_PATTERN.search(quality):
        errors.append("quality-gate-secret-use-forbidden")

    scheduler = _read(root / SCHEDULER_WORKFLOW)
    scheduler_secrets = set(SECRET_PATTERN.findall(scheduler))
    if scheduler_secrets != ALLOWED_SCHEDULER_SECRETS:
        errors.append("scheduler-secret-contract-invalid")
    for marker in ("timeout-minutes: 4", "environment: phase6q-pilot", "persist-credentials: false"):
        if marker not in scheduler:
            errors.append(f"scheduler-hardening-marker-missing:{marker}")

    dependabot = _read(root / DEPENDABOT_POLICY)
    for ecosystem, directory in (("github-actions", "/"), ("npm", "/apps/web"), ("pip", "/")):
        if f'package-ecosystem: "{ecosystem}"' not in dependabot or f'directory: "{directory}"' not in dependabot:
            errors.append(f"dependabot-policy-missing:{ecosystem}")
    if dependabot.count('interval: "weekly"') != 3 or "open-pull-requests-limit:" not in dependabot:
        errors.append("dependabot-bounds-invalid")

    errors = sorted(set(errors))
    return {
        "evidence_version": "phase6q.workflow-security.v1",
        "ok": not errors,
        "workflow_count": len(workflow_paths),
        "action_use_count": action_uses,
        "reviewed_action_count": len(pins),
        "quality_gate_secret_count": len(SECRET_PATTERN.findall(quality)),
        "scheduler_secret_name_count": len(scheduler_secrets),
        "provider_call_count": 0,
        "identifiers_redacted": True,
        "secrets_printed": False,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate pinned and bounded first-party GitHub workflows.")
    parser.add_argument("--json", action="store_true", help="Retained for explicit machine-readable invocation.")
    parser.parse_args()
    result = validate_workflows(ROOT)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
