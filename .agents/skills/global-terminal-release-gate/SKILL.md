---
name: global-terminal-release-gate
description: Build and inspect the Global Terminal source release archive. Use before declaring a phase complete, after release-script changes, or when checking required product source and sensitive/external/generated exclusions.
---

# Global Terminal Release Gate

## Workflow

1. Run the focused release hygiene tests.
2. Build with `python scripts/build_release_zip.py`.
3. Verify `AGENTS.md`, `.agents/skills`, web, backend, API requirements, docs, tests, scripts, static, pages, and lib are present.
4. Verify `.env`, secrets, private data, databases, uploads, external references, node_modules, `.next`, caches, logs, models, and checkpoints are absent.
5. Compare manifest counts with actual ZIP entries.
6. Record the path, counts, inclusions, exclusions, and verdict.
