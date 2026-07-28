# Phase 5H Preflight Report

Updated: 2026-06-20

## Selected Slice

Phase 5H converts the existing War Room map contract/fixture surface into a product-first Global Risk Map journey. The durable benchmark-parity goal remains active.

## Pre-Change Baseline

- `python -m compileall -q app.py lib pages scripts tests backend`: pass.
- `python scripts/run_smoke_tests.py`: pass.
- full pytest with third-party plugin autoload disabled and `-x`: exit 0; one optional skip; two existing cointegration collinearity warnings.
- `python -m py_compile backend/api/app.py`: pass.
- deterministic fixture export: pass, 20 fixtures.
- web test, lint, production build: pass.
- npm high-severity audit: 0 vulnerabilities.
- pre-change release: `dist/global_market_terminal_20260620T031843Z.zip`, 1295 selected files and 1296 ZIP entries.

## Rendered Baseline

`review_workspace/phase5h_visual/baseline-map-desktop.png` proves the current defect:

- contract diagnostics dominate the header and navigation;
- repository-wide gap/envelope counts dominate product status;
- the map is a small lower panel rather than the first-viewport experience;
- fixture mode shows two marker rows and no live/cache layer;
- selected-event news/assets do not react to marker selection;
- map state is not preserved in the URL;
- no explicit map-ready or rendered-marker DOM proof exists.

## Environment Boundary

The project `.env` exists and loads. Phase 5H-relevant provider variables are checked as configured booleans only; values are never logged or exported. OpenSky client variables are configured, but the live OAuth probe currently returns `401 OpenSky OAuth credential rejected`. USGS returned 100 rows and the public news aggregate returned 40 rows in the pre-change smoke. OpenSky produced zero rows and must remain unavailable/error-labeled.

## Preflight Verdict

The baseline is consistent and green. Phase 5H can proceed. Passing tests do not prove map product quality; visual/product and runtime gates remain open.
