# Goal 7 Plan

## Scope

Goal 7 adds three product surfaces without rewriting existing logic:

- Portfolio Quant Lab: editable portfolio state, backtests, research strategy candidates, alpha signals, optimizers, forecasts, attribution, visualizations, stress integration, and data status.
- Live Data Provider Center: explicit provider registry, optional-key diagnostics, live-feed readiness, realtime connector skeletons, and missing-key/data-gap reporting.
- Terminal UX deepening: workspace presets, provider health strip, richer War Room right rail, layer-first map payloads, News/Screener/Crypto/Energy terminal surfaces, and release hygiene tests.

## Guardrails

- No paid provider is required for base launch.
- Missing optional providers degrade gracefully.
- No WorldMonitor source is copied into runtime.
- AIS and flight tracking remain unavailable unless configured and tested.
- Backtests, optimizers, strategies, forecasts, and scenarios are research-only and not advice.

## Verification

- Pre-flight smoke and full pytest pass before feature work.
- New portfolio, provider, UX, and release archive tests are added.
- Final verification requires `python scripts/run_smoke_tests.py` and `python -m pytest -q`.
