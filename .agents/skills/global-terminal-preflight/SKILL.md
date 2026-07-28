---
name: global-terminal-preflight
description: Run and document the Global Terminal repository baseline before a product phase or substantial edit. Use for preflight, baseline verification, current-state audits, or when a phase requires proof that Python, web, security, and release gates pass before coding.
---

# Global Terminal Preflight

## Workflow

1. Read `AGENTS.md`, `docs/ROADMAP.md`, and the active phase prompt.
2. Record the current phase, known product gap, and exact done criteria.
3. Run the commands in the root `AGENTS.md` verification section, using `pytest -q -x` before edits.
4. Count collected tests and record skips and warnings without hiding them.
5. Build the release ZIP and verify web/backend inclusion plus external/private/generated exclusion.
6. Write or update the phase preflight report before product code changes.
7. Stop and select a fix phase if the baseline is inconsistent.
