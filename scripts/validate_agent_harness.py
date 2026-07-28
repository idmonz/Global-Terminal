from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_DOCS = (
    "docs/PLANS.md",
    "docs/SECURITY.md",
    "docs/ROADMAP.md",
    "docs/NEXT_ROADMAP_EXECUTION_PROMPT.md",
    "docs/GOAL_MASTER_ACTIVE_PHASE_DECISION.md",
)


def validate_harness(root: str | Path | None = None) -> dict[str, Any]:
    base = Path(root or Path(__file__).resolve().parents[1]).resolve()
    agents = base / "AGENTS.md"
    active_dir = base / "docs" / "exec-plans" / "active"
    active = sorted(active_dir.glob("*.md")) if active_dir.exists() else []
    missing = [relative for relative in REQUIRED_DOCS if not (base / relative).is_file()]
    skill_count = len(list((base / ".agents" / "skills").glob("*/SKILL.md")))
    agents_bytes = agents.stat().st_size if agents.exists() else 0
    errors: list[str] = []
    if not agents.exists():
        errors.append("AGENTS.md missing")
    if agents_bytes >= 12_000:
        errors.append("AGENTS.md must remain a concise map below 12 KB")
    if len(active) != 1:
        errors.append("Exactly one active execution plan is required")
    if missing:
        errors.append("Missing required docs: " + ", ".join(missing))
    if skill_count != 6:
        errors.append(f"Expected six repository skills, found {skill_count}")
    return {
        "ok": not errors,
        "agents_bytes": agents_bytes,
        "active_plan_count": len(active),
        "active_plans": [path.relative_to(base).as_posix() for path in active],
        "skill_count": skill_count,
        "missing": missing,
        "errors": errors,
    }


def main() -> int:
    report = validate_harness()
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
