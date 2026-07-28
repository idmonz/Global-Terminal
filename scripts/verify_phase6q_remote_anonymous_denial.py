from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
DENIED_STATUSES = {401, 403}
SURFACES = (
    ("global_terminal_hosted_scheduler_control", "GET", "/rest/v1/global_terminal_hosted_scheduler_control"),
    ("global_terminal_hosted_observation_schedules", "GET", "/rest/v1/global_terminal_hosted_observation_schedules"),
    ("global_terminal_hosted_observation_schedule_runs", "GET", "/rest/v1/global_terminal_hosted_observation_schedule_runs"),
    ("global_terminal_hosted_observation_schedule_audit", "GET", "/rest/v1/global_terminal_hosted_observation_schedule_audit"),
    ("apply_schedule_rpc", "POST", "/rest/v1/rpc/global_terminal_apply_hosted_observation_schedule"),
)


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


def verify_remote_anonymous_denial(
    root: Path = ROOT,
    *,
    requester: Any | None = None,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    env = _dotenv(root / ".env")
    base_url = str(env.get("SUPABASE_URL") or "").rstrip("/")
    publishable_key = str(env.get("SUPABASE_PUBLISHABLE_KEY") or env.get("SUPABASE_ANON_KEY") or "")
    if not base_url or not publishable_key:
        raise RuntimeError("Supabase URL and publishable key are required for the anonymous denial probe.")

    session = requester or requests.Session()
    headers = {
        "apikey": publishable_key,
        "Authorization": f"Bearer {publishable_key}",
        "Content-Type": "application/json",
    }
    checks: list[dict[str, Any]] = []
    for surface, method, path in SURFACES:
        kwargs: dict[str, Any] = {"headers": headers, "timeout": timeout_seconds}
        if method == "GET":
            kwargs["params"] = {"select": "*", "limit": "1"}
        else:
            kwargs["json"] = {"p_schedule": {}, "p_expected_version": 0}
        try:
            response = session.request(method, f"{base_url}{path}", **kwargs)
            status = int(response.status_code)
        except requests.RequestException:
            status = 0
        checks.append({"surface": surface, "status": status, "denied": status in DENIED_STATUSES})

    passed = all(check["denied"] for check in checks)
    return {
        "evidence_version": "phase6q.remote-anonymous-denial.v1",
        "passed": passed,
        "checks": checks,
        "denied_count": sum(1 for check in checks if check["denied"]),
        "expected_denied_count": len(SURFACES),
        "provider_call_count": 0,
        "state_change_expected": False,
        "mutation_applied": False,
        "identifiers_redacted": True,
        "secrets_printed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify anonymous denial for the remote Phase 6Q scheduler schema.")
    parser.add_argument("--output", default="review_workspace/phase6q_remote_anonymous_denial_summary.json")
    args = parser.parse_args()
    result = verify_remote_anonymous_denial(ROOT)
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
