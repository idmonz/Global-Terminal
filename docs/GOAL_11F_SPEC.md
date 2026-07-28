# Goal 11F Specification

## Objective

Perform a short pre-Goal12 hotfix gate over the Goal 11E Research OS release.

## Required behavior

- `.env.example` is restored, placeholder-only, and included in release.
- Local secret files remain excluded.
- Advisory and guarantee-style command intent is blocked by the shared command safety layer.
- Descriptive research terminology remains allowed.
- Direct workflow actions return clean research-boundary cards when blocked.
- Optional report HTML bodies are escaped by default before export.
- Energy Brief command-palette actions route to `GENERATE_ENERGY_BRIEF` and create `energy_geopolitics` report items.
- Release package count reporting distinguishes selected source files from the manifest entry.

- Scope: Goal 11F hotfix only; Goal 12 was not implemented.
- Boundary: research-only local workspace, no broker path, no autonomous execution path, no external runtime dependency.
- Verification gates: compileall, smoke tests, full pytest, cleanup dry-run, cleanup execute, and release build.
