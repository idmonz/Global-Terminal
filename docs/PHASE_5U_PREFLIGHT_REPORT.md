# Phase 5U Preflight Report

Updated: 2026-06-29

## Phase

Phase 5U: Map-First War Room Operations Desk.

The user-visible gap is that the existing War Map has real contracts, markers and replay controls, but the first viewport still does not behave like a dense WorldMonitor/worldview-style intelligence desk.

## Acceptance Baseline

Phase 5U must:

- make the map the dominant first-viewport working surface;
- co-locate layer/source truth, selected event, news/event context, timeline/compare and market exposure;
- preserve URL state and honest live/cache/stale/static/proxy/unavailable labels;
- remain usable at 390px without horizontal overflow;
- pass Python, web, visual and release gates.

## Baseline Verification

Recorded before Phase 5U product edits:

- Collected Python tests: `823`.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; python -m pytest -q -x`: passed.
- Existing warnings:
  - FastAPI/Starlette `httpx` deprecation warning.
  - Two existing cointegration collinearity warnings.
- `npm.cmd --prefix apps/web test`: passed; 27 fixtures validated.
- `npm.cmd --prefix apps/web run lint`: passed.
- `npm.cmd --prefix apps/web run build`: passed.
- `npm.cmd --prefix apps/web audit --audit-level=high`: passed; zero high-severity vulnerabilities.

## Release Baseline

Command:

```powershell
python scripts/build_release_zip.py
```

Result:

- ZIP: `dist/global_market_terminal_20260629T142559Z.zip`
- Files selected before manifest: `1463`
- ZIP entries after manifest: `1464`
- Required source areas present: `AGENTS.md`, `.agents/skills`, `apps/web`, `backend`, `lib`, `pages`, `scripts`, `static`, `tests`, and `docs`.
- Secret `.env` is absent. The only `.env*` release entry is the allowed `.env.example`.
- External references, `node_modules`, `.next`, private data and cache directories are absent.

## Browser Baseline

The in-app Browser backend is unavailable in this session. The browser runtime exposed only a Chrome extension connection, so Phase 5U visual QA will use the repository `playwright-core` plus local Chrome fallback and will record that fallback explicitly.

## Verdict

The baseline is consistent and green. Phase 5U can proceed as a focused product change. This report does not prove Phase 5U completion.
