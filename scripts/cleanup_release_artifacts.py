from __future__ import annotations

import sys

from safe_cleanup_generated_artifacts import main as safe_cleanup_main


def main() -> int:
    if "--dry-run" not in sys.argv and "--execute" not in sys.argv:
        sys.argv.append("--execute")
    return safe_cleanup_main()


if __name__ == "__main__":
    raise SystemExit(main())
