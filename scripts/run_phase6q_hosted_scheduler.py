from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.env_loader import load_project_env
from lib.hosted_scheduler_worker import run_hosted_scheduler_once


def main() -> int:
    load_project_env()
    worker_id = f"github-actions-phase6q-{socket.gethostname()[:24]}"
    result = run_hosted_scheduler_once(
        worker_id=worker_id,
        lease_seconds=int(os.getenv("GLOBAL_TERMINAL_HOSTED_SCHEDULER_LEASE_SECONDS", "120") or 120),
    )
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 1 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
