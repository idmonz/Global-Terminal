# Global Terminal Agent Guide

## Product Boundary

- `apps/web`: commercial B2C product.
- `backend/api`: optional API boundary.
- `lib`: reusable providers, normalization, research, quant, and contracts.
- `pages` and `app.py`: internal Streamlit lab and regression reference.
- `static/api-fixtures`: deterministic network-free development fallback.

## Required Workflow

1. Read `docs/ROADMAP.md` and `docs/NEXT_ROADMAP_EXECUTION_PROMPT.md`.
2. Read `docs/PLANS.md` and the single active execution plan for substantial work.
3. Run `$global-terminal-preflight` before product edits.
4. Select one vertical phase and write acceptance criteria before coding.
5. Inspect existing Streamlit and `lib` behavior before adding abstractions.
6. Keep provider, source URL, freshness, caveat, and data gap visible.
7. Use `$global-terminal-cleanroom-reference` for external evidence.
8. Use `$global-terminal-frontend-visual-qa` for UI changes.
9. Run narrow tests, then the full Python/web gates.
10. Run `$global-terminal-release-gate` and inspect the archive.
11. Move the execution plan to completed and write the next goal from evidence.

## Non-Negotiable Rules

- Never claim fixture, proxy, static, stale, or unavailable data is live.
- Never add broker execution, order routing, trade approval, personalized recommendations, entry/exit levels, or autonomous actions.
- Never copy AGPL, NASA, missing-license, unclear-license, or proprietary source/assets into the product.
- Never expose `.env` values, secrets, private paths, user data, caches, uploads, or external archives.
- Never delete, weaken, skip, or rewrite tests merely to pass.
- Never report a visual pass before inspecting screenshots and renderer-ready state.
- Keep Streamlit-only rendering out of reusable `lib` boundaries.
- Extend API contracts additively and keep fixtures deterministic.

## Verification Commands

```powershell
python -m compileall -q app.py lib pages scripts tests backend
python scripts/validate_agent_harness.py
python scripts/run_smoke_tests.py
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest -q
python -m py_compile backend/api/app.py
python scripts/export_api_fixtures.py
npm.cmd --prefix apps/web test
npm.cmd --prefix apps/web run lint
npm.cmd --prefix apps/web run build
npm.cmd --prefix apps/web audit --audit-level=high
python scripts/build_release_zip.py
```

## Completion Standard

A phase is complete only when the user journey works, source truth is honest, focused and broad tests pass, desktop/mobile screenshots are inspected, charts/maps are nonblank where required, and the release boundary is verified.
