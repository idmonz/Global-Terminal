from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


EVIDENCE_VERSION = "phase6q.hosted-rls.v1"
DEFAULT_MAX_AGE_HOURS = 168
MAX_CLOCK_SKEW = timedelta(minutes=5)

REQUIRED_TRUE = (
    "passed",
    "remote_schema_verified",
    "account_identities_distinct",
    "tenant_scopes_distinct",
    "optimistic_conflict_verified",
    "immutable_audit_verified",
    "deleted_schedule_replacement_verified",
    "original_account_document_restored",
    "identifiers_redacted",
)
REQUIRED_FALSE = (
    "operator_gate_changed",
    "hosted_worker_invoked",
    "secrets_printed",
)
REQUIRED_ZERO = (
    "cross_tenant_schedule_rows_visible",
    "cross_tenant_run_rows_visible",
    "cross_tenant_audit_rows_visible",
    "provider_call_count",
)
REQUIRED_KEYS = {
    "evidence_version",
    "captured_at",
    *REQUIRED_TRUE,
    *REQUIRED_FALSE,
    *REQUIRED_ZERO,
}
OPTIONAL_KEYS = {"hosted_scheduler_verified"}


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def validate_phase6q_hosted_rls_summary(
    payload: Any,
    *,
    now: datetime | None = None,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
) -> dict[str, object]:
    reasons: list[str] = []
    if not isinstance(payload, dict):
        return {"passed": False, "reasons": ["evidence-not-object"]}

    keys = set(payload)
    missing = sorted(REQUIRED_KEYS - keys)
    unknown = sorted(keys - REQUIRED_KEYS - OPTIONAL_KEYS)
    if missing:
        reasons.append("required-fields-missing")
    if unknown:
        reasons.append("unexpected-fields-present")

    if payload.get("evidence_version") != EVIDENCE_VERSION:
        reasons.append("evidence-version-invalid")

    for key in REQUIRED_TRUE:
        if type(payload.get(key)) is not bool or payload.get(key) is not True:
            reasons.append(f"{key}-not-true")
    for key in REQUIRED_FALSE:
        if type(payload.get(key)) is not bool or payload.get(key) is not False:
            reasons.append(f"{key}-not-false")
    for key in REQUIRED_ZERO:
        if type(payload.get(key)) is not int or payload.get(key) != 0:
            reasons.append(f"{key}-not-zero")

    if "hosted_scheduler_verified" in payload and payload.get("hosted_scheduler_verified") is not False:
        reasons.append("hosted-scheduler-verification-promoted")

    captured_at = _parse_timestamp(payload.get("captured_at"))
    age_hours: float | None = None
    if captured_at is None:
        reasons.append("captured-at-invalid")
    else:
        checked_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        age = checked_at - captured_at
        age_hours = round(age.total_seconds() / 3600, 3)
        if age < -MAX_CLOCK_SKEW:
            reasons.append("captured-at-in-future")
        if max_age_hours <= 0 or age > timedelta(hours=max_age_hours):
            reasons.append("evidence-expired")

    return {
        "passed": not reasons,
        "reasons": sorted(set(reasons)),
        "evidence_version": EVIDENCE_VERSION,
        "age_hours": age_hours,
        "required_field_count": len(REQUIRED_KEYS),
        "unexpected_field_count": len(unknown),
        "identifiers_redacted": payload.get("identifiers_redacted") is True,
        "secrets_printed": payload.get("secrets_printed") is True,
        "provider_call_count": payload.get("provider_call_count") if type(payload.get("provider_call_count")) is int else None,
        "hosted_scheduler_verified": False,
    }


def verify_file(path: Path, *, max_age_hours: int = DEFAULT_MAX_AGE_HOURS) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"passed": False, "reasons": ["evidence-file-missing"]}
    except (OSError, ValueError, TypeError):
        return {"passed": False, "reasons": ["evidence-file-invalid"]}
    return validate_phase6q_hosted_rls_summary(payload, max_age_hours=max_age_hours)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify redacted Phase 6Q Account A/B hosted RLS evidence without printing its payload."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="review_workspace/phase6q_hosted_rls_summary.json",
    )
    parser.add_argument("--max-age-hours", type=int, default=DEFAULT_MAX_AGE_HOURS)
    args = parser.parse_args()
    result = verify_file(Path(args.path).resolve(), max_age_hours=args.max_age_hours)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
