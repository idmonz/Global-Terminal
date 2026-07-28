from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(ROOT))

from lib.hosted_scheduler_operations import (  # noqa: E402
    DEFAULT_EVIDENCE_MAX_AGE_HOURS,
    validate_hosted_scheduler_evidence,
)


def verify_file(path: Path, *, max_age_hours: int = DEFAULT_EVIDENCE_MAX_AGE_HOURS) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"passed": False, "reasons": ["evidence-file-missing"]}
    except (OSError, ValueError, TypeError):
        return {"passed": False, "reasons": ["evidence-file-invalid"]}
    return validate_hosted_scheduler_evidence(payload, max_age_hours=max_age_hours)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify redacted Phase 6Q hosted scheduler evidence without printing its payload.")
    parser.add_argument(
        "path",
        nargs="?",
        default=os.getenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_EVIDENCE_PATH") or "review_workspace/phase6q_hosted_handoff_summary.json",
    )
    parser.add_argument("--max-age-hours", type=int, default=DEFAULT_EVIDENCE_MAX_AGE_HOURS)
    args = parser.parse_args()
    result = verify_file(Path(args.path).resolve(), max_age_hours=args.max_age_hours)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
