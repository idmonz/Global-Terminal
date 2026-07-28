# Phase 5X Test And Release Report

Updated: 2026-06-30

## Tests Run

Pre-change/continuation checks:

- `npm --prefix apps/web test`: passed.
- `npm --prefix apps/web run build`: passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -x`: passed before Phase 5X edits.

Focused Phase 5X checks:

- `python -m py_compile lib/equity_provider_breadth.py lib/symbol_intelligence.py`: passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_phase5x_equity_provider_breadth.py tests/test_phase5n_symbol_intelligence.py -q`: passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_goal11f_env_example_release_setup.py tests/test_phase5x_equity_provider_breadth.py -q`: passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_phase5x_equity_provider_breadth.py tests/test_phase5n_symbol_intelligence.py tests/test_api_fixture_export.py tests/test_api_backend_routes.py -q`: passed.

Broad gates:

- `python -m compileall -q app.py lib pages scripts tests backend`: passed.
- `python scripts/run_smoke_tests.py`: passed.
- `python scripts/export_api_fixtures.py`: passed, 27 fixtures.
- `npm.cmd --prefix apps/web test`: passed.
- `npm.cmd --prefix apps/web run lint`: passed.
- `npm.cmd --prefix apps/web run build`: passed.
- `npm.cmd --prefix apps/web audit --audit-level=high`: passed, 0 vulnerabilities.
- `GT_BASE_URL=http://127.0.0.1:3040 npm.cmd --prefix apps/web run test:runtime-api`: passed. One earlier run without the expected local server failed with `ECONNREFUSED 127.0.0.1:3031`; rerun with the production harness available passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`: passed.

Known warnings:

- Existing FastAPI/Starlette `httpx` deprecation warning.
- Existing cointegration collinearity warnings in quant diagnostics tests.

## Visual QA

- `npm.cmd --prefix apps/web run visual:phase5x` online passed against `http://127.0.0.1:3040`.
- `npm.cmd --prefix apps/web run visual:phase5x` offline passed against `http://127.0.0.1:3041` with invalid API base.

Screenshots are listed in `docs/PHASE_5X_VISUAL_QA_REPORT.md`.

## Release

Command:

```powershell
python scripts/build_release_zip.py
```

Result:

- ZIP: `dist/global_market_terminal_20260630T131127Z.zip`
- Entries: 1,490.
- Files packaged: 1,489.
- `.env.example`: included.
- `apps/web/src/`: included.
- Forbidden scan: no `.env`, `external`, `external (2)`, `node_modules`, `.next`, or `data/private` entries found.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
