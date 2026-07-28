# Phase 5W Implementation Report

Date: 2026-06-30

## Outcome

Phase 5W converted the optional local FastAPI runtime from a hidden dependency into a visible product boundary.

The web product now exposes a compact `Runtime API` chip in the top status cluster. When FastAPI is reachable, it shows `online` with route and provider counts. When FastAPI is offline, `live-if-available` routes still fall back to deterministic fixtures/catalog rows, but the UI no longer lets that look like a live-only product.

This phase did not complete benchmark parity. It improved local runtime operation and source-truth visibility.

## Implemented

- Added `runtime_health` API envelope via `build_api_runtime_health_payload`.
- Added FastAPI route `GET /api/runtime-health`.
- Added Next.js runtime health fetcher with timeout-safe offline state.
- Added visible `RuntimeHealthChip` in the top bar.
- Added `scripts/start_local_product.py` to start/reuse FastAPI and Next safely.
- Added production/dev launcher checks for:
  - `http://127.0.0.1:8000/api/runtime-health`
  - `http://127.0.0.1:3000/?view=home&mode=fixture`
- Added Phase 5W visual harness.
- Added tests for runtime health contract, backend route exposure, launcher dry-run safety, and UI markers.

## Runtime State

Observed with local runtime running:

- FastAPI: reachable on `http://127.0.0.1:8000`.
- Runtime health: `api-importable`.
- Manifest count shown in UI: 37 routes.
- Provider rows shown in UI: 250 providers/health rows.
- Next production server: reachable on `http://127.0.0.1:3000`.
- AAPL `live-if-available`: runtime chip online; chart ready; 184 chart points in the final production visual harness.

Observed launcher behavior:

- Reuses already-running FastAPI/Next when health checks pass.
- Starts FastAPI via `python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000`.
- Starts Next via `npm --prefix apps/web run dev` by default or `npm --prefix apps/web run start` with `--production`.
- Does not print `.env` values or API keys.
- Reports occupied-port failures instead of killing unknown processes.

## Files Changed

- `lib/api_contracts.py`
- `backend/api/app.py`
- `apps/web/src/lib/contracts.ts`
- `apps/web/src/lib/fixtures.ts`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/scripts/validate-runtime-ui.mjs`
- `apps/web/scripts/capture-phase5w.mjs`
- `apps/web/package.json`
- `scripts/start_local_product.py`
- `tests/test_phase5w_runtime_orchestration.py`
- `tests/test_api_backend_routes.py`
- `static/api-fixtures/manifest.json`

## Important Limits

- A reachable API does not mean every provider is live. Row-level source status still controls live/cache/stale/fixture/unavailable truth.
- The launcher is local only. It is not hosted deployment, auth, billing, alert delivery, background refresh, or observability.
- Free-first provider depth remains uneven. Earnings/calendar/SEC breadth, licensed fundamentals, OPRA-grade options, AIS, verified flight, sanctions, and full benchmark symbol coverage remain open.
- Dev server visual QA can be distorted by Fast Refresh when files are being edited. Final Phase 5W visual proof used the production Next server after `npm --prefix apps/web run build`.

## Verification

- `python -m py_compile lib/api_contracts.py backend/api/app.py scripts/start_local_product.py`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_phase5w_runtime_orchestration.py tests/test_api_backend_routes.py -q`
- `python scripts/export_api_fixtures.py`
- `npm --prefix apps/web test`
- `npm --prefix apps/web run lint`
- `npm --prefix apps/web run build`
- `npm --prefix apps/web audit --audit-level=high`
- `python scripts/start_local_product.py --production --wait-seconds 60`
- `GT_EXPECT_RUNTIME=online npm --prefix apps/web run visual:phase5w`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`

Known warnings:

- Existing FastAPI/Starlette `httpx` deprecation warning.
- Existing cointegration collinearity warnings.
