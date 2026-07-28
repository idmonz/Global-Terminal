# Recovery Failure Prevention Policy

## Cleanup Safety

- Do not use broad shell deletion for repository cleanup.
- Do not use PowerShell wildcard cleanup commands against source folders.
- Use `scripts/safe_cleanup_generated_artifacts.py` for generated artifacts.
- The cleanup script must default to dry-run mode and require `--execute` before deleting anything.
- The cleanup script may remove only generated artifacts: `__pycache__/`, `.pytest_cache/`, `*.pyc`, `*.pyo`, `*.log`, and `data/cache/`.
- Cleanup must refuse to operate outside the project root.
- Cleanup must refuse to remove source files.

## Manifest And Hash Policy

- Critical source expectations must be encoded in `docs/CANONICAL_EXPECTATIONS.json`.
- Future recovery or phase work should update expectations only when the implementation and tests move together.
- Source deletion detection is required through canonical guard tests before new phase work starts.

## Immutable Core Module Policy

The following modules are treated as immutable baselines unless a phase explicitly requires scoped extension with tests:

- `lib/market_data.py`
- `lib/global_markets.py`
- `lib/heatmaps.py`
- `lib/data_status.py`
- `lib/cache.py`
- `lib/crypto_derivatives.py`
- `lib/crypto_prices.py`
- `lib/crypto_onchain.py`
- `lib/crypto_scenarios.py`
- `lib/equity_breadth.py`
- `lib/equity_scenarios.py`
- `lib/energy_data.py`
- `lib/oil_flows.py`
- `lib/geopolitical_news.py`
- `lib/worldmonitor_adapter.py`
- `lib/risk.py`
- `lib/stress_tests.py`
- `lib/scenario_engine.py`

## Regression Test Policy

- Run `python scripts/run_smoke_tests.py` before major phase work.
- Run `python -m pytest -q` before major phase work.
- Add regression guards for recovered public functions, static row counts, and page-level feature labels.
- Do not remove tests to make a build pass.
- Do not weaken tests to bypass source deletion, placeholder code, or recommendation-language violations.

## Data And Compliance Policy

- Do not fake live data.
- Estimated or proxy data must be labeled as estimated/proxy and include caveats.
- Do not add recommendation language.
- Neutral analysis may summarize evidence, risks, uncertainty, scenarios, data gaps, and watch-points.
- Future `/goal` sessions must start with a pre-flight test gate before implementation.
