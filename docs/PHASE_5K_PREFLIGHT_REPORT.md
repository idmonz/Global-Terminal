# Phase 5K Preflight Report

Updated: 2026-06-21

## Verdict

The repository baseline is green and Phase 5K is the correct next vertical slice. The commercial Next.js product has no Portfolio And Risk route: the canonical `/?view=portfolio-risk` URL currently falls through to the contract-diagnostics Market view. Streamlit contains substantial portfolio research behavior, but its state, DataFrames, Plotly figures, and private JSON storage are not a commercial web product.

The durable benchmark-parity goal remains active.

## Current Product Gap

- No product-first holdings-to-risk journey exists in `apps/web`.
- No additive `portfolio_risk` API envelope, runtime route, or deterministic privacy-safe fixture exists.
- The current unknown-route fallback exposes Market contract diagnostics instead of a portfolio product.
- Existing portfolio math is reusable, but some legacy functions fill missing return observations with zero. Phase 5K must add overlap/sample gates and must not treat missing returns as zero at the web contract boundary.
- Existing factor routing may depend on optional OpenBB paths and proxy factors; model/source/coverage must remain explicit.
- Existing stress scenarios are deterministic estimates, not historical replay or a covariance transmission model.

## Baseline Evidence

Commands run from the authoritative `Global Terminal` root:

- `python -m compileall -q app.py lib pages scripts tests backend`: passed.
- `python scripts/run_smoke_tests.py`: passed; portfolio, risk, factor, attribution, stress, report, API, and research modules imported.
- `python -m pytest -q -x`: passed at 100%.
- `npm.cmd --prefix apps/web test`: passed; 21 fixtures and runtime boundaries validated.
- `npm.cmd --prefix apps/web run lint`: passed.
- `npm.cmd --prefix apps/web run build`: passed on Next.js 16.2.9.
- `npm.cmd --prefix apps/web audit --audit-level=high`: 0 vulnerabilities.
- `python scripts/build_release_zip.py`: passed; 1,336 selected source files and 1,337 ZIP entries including the manifest.

Warnings retained honestly:

- FastAPI TestClient notes the future Starlette/httpx2 transition.
- Existing cointegration tests emit collinearity warnings for deliberately near-collinear inputs.

Baseline release:

`dist/global_market_terminal_20260621T123604Z.zip`

Baseline visual:

`review_workspace/phase5k_visual/baseline-portfolio-route.png`

Observed at 1600x1000: the requested portfolio URL renders Market Intelligence contract diagnostics. This is a failed product-parity state, not a portfolio fallback.

## Existing Engine Inventory

- `portfolio_state.py`: private JSON storage, normalization, weights, demo rows.
- `portfolio_backtester.py`: history acquisition, alignment, return/equity/drawdown and benchmark metrics.
- `risk.py`: volatility, downside risk, VaR/CVaR, beta, drawdown and risk contribution helpers.
- `performance_attribution.py`: return, risk, drawdown, sector, asset-class and turnover attribution.
- `factor_engine.py` and `portfolio_factor_router.py`: proxy factor regression and optional source-aware factor inputs.
- `stress_tests.py`: bounded deterministic hypothetical shocks.
- `portfolio_quant_lab.py`: Streamlit-lab orchestration and research disclosure.
- report/research modules: local-first research context and artifact paths, requiring a privacy-safe adapter before portfolio use.

## Phase 5K Acceptance Boundary

Phase 5K may proceed only with:

1. fictional deterministic fixture holdings and local/private runtime inputs;
2. no quantities, costs, account identifiers, or private holdings in URLs, logs, release screenshots, static fixtures, external AI, or release archives;
3. source-labeled valuation/history with explicit coverage and missing-symbol rows;
4. overlap/sample gates for return, correlation, factor, attribution, and stress calculations;
5. a product-first desktop/mobile workflow with nonblank charts, matrix, holdings and stress tables;
6. full Python/web/security/release regression after implementation.

Outputs remain descriptive research calculations, not advice, recommendations, rebalancing instructions, broker actions, or execution.
